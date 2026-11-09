// E3DLiveBridge — add-in do AVEVA E3D Design que expõe a sessão AO VIVO via HTTP local.
//
//   Cliente MCP -> e3d_mcp.py -> http://localhost:8765/api/* (token) -> este add-in -> thread de UI do E3D
//
// Regras de segurança (iguais ao all3D-MCP):
//   * escuta só em localhost e exige o token gravado em %LOCALAPPDATA%\E3DLiveBridge\token.txt;
//   * atua como o usuário logado, com as permissões dele;
//   * toda escrita roda dentro de UndoTransaction; erro => AbortTransaction (nada fica pela metade);
//   * SAVEWORK só pelo endpoint savework com confirm="SAVEWORK" (o MCP exige frase do usuário).
//
// Compila com o csc.exe do .NET Framework 4 (C# 5): sem interpolação, sem ?. , sem out var.
// API verificada no E3D 3.1 (Aveva.Core.*). Itens marcados [TESTAR-E3D] ainda não foram vistos rodando.

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Aveva.ApplicationFramework;
using Aveva.Core.Database;
using Aveva.Core.Database.Filters;
using Aveva.Core.Utilities.Undo;
using PmlCommand = Aveva.Core.Utilities.CommandLine.Command;
using ATT = Aveva.Core.Database.DbAttributeInstance;

namespace E3DLive
{
    public sealed class E3DLiveBridgeAddin : IAddinInjected
    {
        private BridgeServer _server;
        private Control _ui;

        public string Name { get { return "E3DLiveBridge"; } }
        public string Description { get { return "Ponte local MCP para a sessão E3D ao vivo"; } }

        public void Start(IDependencyResolver resolver) { Init(); }
        public void Start(ServiceManager serviceManager) { /* intencionalmente vazio (evita iniciar duas vezes) */ }

        private void Init()
        {
            try
            {
                if (_server != null) return;
                _ui = new Control();
                IntPtr h = _ui.Handle; // cria o handle na thread de UI do E3D
                GC.KeepAlive(h);
                _server = new BridgeServer(_ui);
                _server.Start();
                Console.WriteLine("[E3DLiveBridge] ouvindo em " + _server.Url);
            }
            catch (Exception ex)
            {
                // Start nunca pode lançar: derrubaria o E3D.
                Console.WriteLine("[E3DLiveBridge] falhou ao iniciar: " + ex.Message);
            }
        }

        public void Stop()
        {
            try { if (_server != null) _server.Stop(); } catch { }
            try { if (_ui != null) _ui.Dispose(); } catch { }
        }
    }

    internal sealed class BridgeServer
    {
        private readonly Control _ui;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer { MaxJsonLength = 64 * 1024 * 1024 };
        private HttpListener _listener;
        private Thread _thread;
        private volatile bool _run;
        private string _token;
        private int _pending;          // transações da ponte desde o último SAVEWORK
        private int _runSeq;
        private readonly string _work;
        public string Url;

        public BridgeServer(Control ui)
        {
            _ui = ui;
            int port;
            if (!int.TryParse(Environment.GetEnvironmentVariable("E3D_BRIDGE_PORT"), out port)) port = 8765;
            Url = "http://localhost:" + port + "/";
            string pub = Environment.GetEnvironmentVariable("PUBLIC") ?? @"C:\Users\Public";
            _work = Environment.GetEnvironmentVariable("E3D_BRIDGE_WORK") ?? Path.Combine(pub, @"E3DLiveBridge\work");
        }

        public void Start()
        {
            Directory.CreateDirectory(_work);
            byte[] b = new byte[24];
            using (RandomNumberGenerator rng = RandomNumberGenerator.Create()) rng.GetBytes(b);
            _token = Convert.ToBase64String(b).Replace('+', '-').Replace('/', '_').TrimEnd('=');
            string dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "E3DLiveBridge");
            Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, "token.txt"), _token);

            _listener = new HttpListener();
            _listener.Prefixes.Add(Url);
            _listener.Start();
            _run = true;
            _thread = new Thread(Loop) { IsBackground = true, Name = "E3DLiveBridge" };
            _thread.Start();
        }

        public void Stop()
        {
            _run = false;
            try { _listener.Stop(); } catch { }
        }

        private void Loop()
        {
            while (_run)
            {
                HttpListenerContext ctx;
                try { ctx = _listener.GetContext(); } catch { break; }
                ThreadPool.QueueUserWorkItem(delegate { Serve(ctx); });
            }
        }

        private void Serve(HttpListenerContext ctx)
        {
            Dictionary<string, object> result;
            int code = 200;
            try
            {
                if (ctx.Request.HttpMethod != "POST" || !ctx.Request.IsLocal)
                {
                    code = 405; result = Fail("só POST local");
                }
                else if (!FixedEquals(ctx.Request.Headers["X-E3D-Token"], _token))
                {
                    code = 401; result = Fail("token inválido");
                }
                else
                {
                    string body;
                    using (StreamReader r = new StreamReader(ctx.Request.InputStream, Encoding.UTF8)) body = r.ReadToEnd();
                    Dictionary<string, object> p = string.IsNullOrEmpty(body) ? new Dictionary<string, object>()
                        : _json.Deserialize<Dictionary<string, object>>(body);
                    string ep = ctx.Request.Url.AbsolutePath.Replace("/api/", "").Trim('/');
                    // Toda chamada à API do E3D acontece na thread de UI.
                    result = (Dictionary<string, object>)_ui.Invoke(new Func<Dictionary<string, object>>(delegate { return Dispatch(ep, p); }));
                }
            }
            catch (Exception ex)
            {
                Exception inner = ex.InnerException ?? ex;
                result = Fail(inner.Message);
            }
            byte[] data = Encoding.UTF8.GetBytes(_json.Serialize(result));
            try
            {
                ctx.Response.StatusCode = code;
                ctx.Response.ContentType = "application/json; charset=utf-8";
                ctx.Response.OutputStream.Write(data, 0, data.Length);
                ctx.Response.Close();
            }
            catch { }
        }

        private Dictionary<string, object> Dispatch(string ep, Dictionary<string, object> p)
        {
            try
            {
                switch (ep)
                {
                    case "health": return Health();
                    case "element": return Element(S(p, "name"), L(p, "attributes"));
                    case "members": return Members(p);
                    case "collect": return Collect(p);
                    case "find": return Find(p);
                    case "connections": return Connections(S(p, "name"));
                    case "evaluate": return Evaluate(S(p, "name"), S(p, "expression"));
                    case "run": return Run(p);
                    case "setattrs": return SetAttrs(p);
                    case "undo": return Undo(I(p, "steps", 1));
                    case "view": return View(S(p, "name"));
                    case "screenshot": return Screenshot();
                    case "savework": return SaveWork(p);
                    default: return Fail("endpoint desconhecido: " + ep);
                }
            }
            catch (Exception ex)
            {
                return Fail(ex.Message);
            }
        }

        // ------------------------------------------------------------ leitura

        private Dictionary<string, object> Health()
        {
            Dictionary<string, object> r = Ok();
            r["project"] = Project.CurrentProject.Code;
            r["user"] = Project.CurrentProject.UserName;
            r["mdb"] = MDB.CurrentMDB.Name;
            DbElement ce = CurrentElement.Element;
            r["ce"] = (ce != null && ce.IsValid) ? ce.GetAsString(ATT.FLNM) : null;
            r["ce_type"] = (ce != null && ce.IsValid) ? ce.ElementType.Name : null;
            r["pending_changes"] = _pending > 0;
            r["bridge_transactions_unsaved"] = _pending;
            r["bridge"] = "E3DLiveBridge 0.1";
            return r;
        }

        private static readonly string[] DefaultAttrs = { "NAME", "TYPE", "OWNER", "DESC", "POS", "ORI", "SPRE", "CATR", "PURP", "BUIL", "SHOP" };

        private Dictionary<string, object> Element(string name, List<string> attrs)
        {
            DbElement e = Get(name);
            Dictionary<string, object> r = Ok();
            r["name"] = e.GetAsString(ATT.FLNM);
            r["type"] = e.ElementType.Name;
            r["owner"] = e.Owner.IsValid ? e.Owner.GetAsString(ATT.FLNM) : null;
            r["ref"] = RefOf(e);
            r["attributes"] = ReadAttrs(e, attrs.Count > 0 ? attrs.ToArray() : DefaultAttrs);
            Dictionary<string, object> w = new Dictionary<string, object>();
            w["pos"] = Eval(e, "POS WRT /*");
            w["ori"] = Eval(e, "ORI WRT /*");
            r["world"] = w;
            return r;
        }

        private Dictionary<string, object> Members(Dictionary<string, object> p)
        {
            DbElement root = Get(S(p, "name"));
            int depth = Math.Max(1, Math.Min(I(p, "depth", 1), 6));
            string type = S(p, "type");
            int budget = 3000;
            Dictionary<string, object> r = Ok();
            r["tree"] = Node(root, depth, type, ref budget);
            r["truncated"] = budget <= 0;
            return r;
        }

        private Dictionary<string, object> Node(DbElement e, int depth, string type, ref int budget)
        {
            budget--;
            Dictionary<string, object> n = new Dictionary<string, object>();
            n["name"] = e.GetAsString(ATT.FLNM);
            n["type"] = e.ElementType.Name;
            if (depth > 0 && budget > 0)
            {
                List<object> kids = new List<object>();
                foreach (DbElement m in e.Members())
                {
                    if (budget <= 0) break;
                    if (!string.IsNullOrEmpty(type) && !TypeMatches(m, type)) continue;
                    kids.Add(Node(m, depth - 1, type, ref budget));
                }
                n["members"] = kids;
            }
            return n;
        }

        private Dictionary<string, object> Collect(Dictionary<string, object> p)
        {
            DbElement scope = Get(S(p, "scope"));
            List<BaseFilter> fs = new List<BaseFilter>();
            List<string> types = L(p, "types");
            if (types.Count > 0)
            {
                List<DbElementType> ts = new List<DbElementType>();
                foreach (string t in types) ts.Add(TypeOf(t));
                fs.Add(new TypeFilter(ts.ToArray()));
            }
            string expr = S(p, "expression");
            if (!string.IsNullOrEmpty(expr)) fs.Add(new ExpressionFilter(DbExpression.Parse(expr)));
            BaseFilter f = fs.Count == 0 ? (BaseFilter)new TrueFilter() : fs.Count == 1 ? fs[0] : new AndFilter(fs.ToArray());
            int limit = Math.Min(I(p, "limit", 500), 5000);
            string[] attrs = L(p, "attributes").ToArray();
            if (attrs.Length == 0) attrs = new[] { "NAME", "TYPE" };
            List<object> rows = new List<object>();
            int count = 0;
            foreach (DbElement e in new DBElementCollection(scope, f))
            {
                count++;
                if (rows.Count < limit) rows.Add(ReadAttrs(e, attrs));
            }
            Dictionary<string, object> r = Ok();
            r["count"] = count; r["elements"] = rows; r["truncated"] = count > limit;
            return r;
        }

        private Dictionary<string, object> Find(Dictionary<string, object> p)
        {
            string scopeName = S(p, "scope");
            DbElement scope = string.IsNullOrEmpty(scopeName) ? MDB.CurrentMDB.GetFirstWorld(DbType.Design) : Get(scopeName);
            BaseFilter f = new AttributeLikeFilter(ATT.NAME, S(p, "pattern"));
            string type = S(p, "type");
            if (!string.IsNullOrEmpty(type)) f = new AndFilter(new TypeFilter(TypeOf(type)), f);
            int limit = I(p, "limit", 200);
            List<object> rows = new List<object>();
            int count = 0;
            foreach (DbElement e in new DBElementCollection(scope, f))
            {
                count++;
                if (rows.Count < limit) rows.Add(ReadAttrs(e, new[] { "NAME", "TYPE", "OWNER" }));
            }
            Dictionary<string, object> r = Ok();
            r["count"] = count; r["elements"] = rows;
            return r;
        }

        private Dictionary<string, object> Connections(string name)
        {
            DbElement e = Get(name);
            Dictionary<string, object> r = Ok();
            r["element"] = e.GetAsString(ATT.FLNM);
            r["type"] = e.ElementType.Name;
            List<object> items = new List<object>();
            string[] a = { "NAME", "TYPE", "CREF", "HREF", "TREF", "HCON", "TCON", "HBOR", "TBOR", "PBOR" };
            if (TypeMatches(e, "NOZZ") || TypeMatches(e, "BRAN"))
                items.Add(ReadAttrs(e, a));
            foreach (DbElement m in new DBElementCollection(e, new TypeFilter(new[] { TypeOf("NOZZ"), TypeOf("BRAN") })))
                items.Add(ReadAttrs(m, a));
            r["items"] = items;
            List<object> open = new List<object>();
            foreach (object o in items)
            {
                Dictionary<string, object> d = (Dictionary<string, object>)o;
                bool isNoz = "NOZZ".Equals(d["TYPE"]);
                if (isNoz && IsNull(d, "CREF")) open.Add(d["NAME"] + " (bocal sem ligação)");
                if (!isNoz && IsNull(d, "HREF")) open.Add(d["NAME"] + " (cabeça livre)");
                if (!isNoz && IsNull(d, "TREF")) open.Add(d["NAME"] + " (cauda livre)");
            }
            r["open_ends"] = open;
            return r;
        }

        private Dictionary<string, object> Evaluate(string name, string expression)
        {
            Dictionary<string, object> r = Ok();
            r["value"] = Get(name).EvaluateString(DbExpression.Parse(expression));
            return r;
        }

        // ------------------------------------------------------------ escrita

        private Dictionary<string, object> Run(Dictionary<string, object> p)
        {
            DbElement scope = Get(S(p, "scope"));
            string macro = S(p, "macro");
            string desc = S(p, "description") ?? "E3D Live MCP";
            string u = macro.ToUpperInvariant();
            if (u.Contains("SAVEWORK") || u.Contains("QUITWORK") || u.Contains("GETWORK"))
                return Fail("macro contém comando de gravação/descarte — bloqueado pela ponte");

            Dictionary<string, string> before = Fingerprint(scope);
            int n = Interlocked.Increment(ref _runSeq);
            string mac = Path.Combine(_work, "run_" + n + ".mac");
            string res = Path.Combine(_work, "run_" + n + ".err");
            string wrap = Path.Combine(_work, "wrap_" + n + ".mac");
            File.WriteAllText(mac, macro, new UTF8Encoding(false));
            if (File.Exists(res)) File.Delete(res);
            // [TESTAR-E3D] handle any captura o erro de uma macro chamada com $M.
            string wrapper =
                "!!e3dLiveErr = ''\r\n" +
                scope.GetAsString(ATT.FLNM) + "\r\n" +
                "$M /" + mac + "\r\n" +
                "handle any\r\n  !!e3dLiveErr = !!error.text\r\nendhandle\r\n" +
                "!e3dLiveOut = ARRAY()\r\n!e3dLiveOut.append(!!e3dLiveErr)\r\n" +
                "!e3dLiveF = object FILE(|" + res + "|)\r\n!e3dLiveF.writefile('OVERWRITE', !e3dLiveOut)\r\n";
            File.WriteAllText(wrap, wrapper, new UTF8Encoding(false));

            UndoTransaction tx = UndoTransaction.GetUndoTransaction();
            tx.StartTransaction("E3D Live MCP: " + desc);
            string error = null;
            try
            {
                PmlCommand.CreateCommand("$M /" + wrap).Run();
                error = File.Exists(res) ? File.ReadAllText(res).Trim() : "a macro não terminou (sem arquivo de resultado)";
            }
            catch (Exception ex) { error = ex.Message; }

            if (!string.IsNullOrEmpty(error))
            {
                try { tx.AbortTransaction(); } catch (Exception ab) { error += " | rollback falhou: " + ab.Message; }
                Dictionary<string, object> f = Fail(error);
                f["rolled_back"] = true;
                return f;
            }
            tx.EndTransaction();
            _pending++;

            Dictionary<string, string> after = Fingerprint(scope);
            List<object> created = new List<object>(), modified = new List<object>();
            foreach (KeyValuePair<string, string> kv in after)
            {
                string old;
                if (!before.TryGetValue(kv.Key, out old)) created.Add(NameOfRef(kv.Key));
                else if (old != kv.Value) modified.Add(NameOfRef(kv.Key));
            }
            List<object> deleted = new List<object>();
            foreach (string k in before.Keys) if (!after.ContainsKey(k)) deleted.Add(k);
            Dictionary<string, object> r = Ok();
            r["created"] = created; r["modified"] = modified; r["deleted_refs"] = deleted;
            r["transaction"] = desc; r["saved"] = false;
            return r;
        }

        private static readonly string[] FpAttrs = { "NAME", "DESC", "POS", "ORI", "DIAM", "HEIG", "XLEN", "YLEN", "ZLEN", "DTOP", "DBOT",
            "SPRE", "CATR", "HPOS", "TPOS", "HREF", "TREF", "CREF", "BUIL", "SHOP", "PSPE", "ARRI", "LEAV" };

        private Dictionary<string, string> Fingerprint(DbElement scope)
        {
            Dictionary<string, string> d = new Dictionary<string, string>();
            DBElementCollection c = new DBElementCollection(scope, new TrueFilter());
            c.IncludeRoot = true;
            int k = 0;
            foreach (DbElement e in c)
            {
                if (++k > 50000) break;
                StringBuilder sb = new StringBuilder();
                foreach (KeyValuePair<string, object> kv in ReadAttrs(e, FpAttrs)) sb.Append(kv.Key).Append('=').Append(kv.Value).Append(';');
                d[RefOf(e)] = sb.ToString();
            }
            return d;
        }

        private Dictionary<string, object> SetAttrs(Dictionary<string, object> p)
        {
            DbElement e = Get(S(p, "name"));
            Dictionary<string, object> values = (Dictionary<string, object>)p["values"];
            UndoTransaction tx = UndoTransaction.GetUndoTransaction();
            tx.StartTransaction("E3D Live MCP: atributos de " + e.GetAsString(ATT.FLNM));
            Dictionary<string, object> back = new Dictionary<string, object>();
            try
            {
                e.Claim();
                foreach (KeyValuePair<string, object> kv in values)
                {
                    // Atribuição via PML1 aceita unidades e referências (ex. 'SPRE SPCOMPONENT /A3B/X').
                    PmlCommand.CreateCommand(e.GetAsString(ATT.FLNM)).Run();
                    PmlCommand.CreateCommand(kv.Key.ToUpperInvariant() + " " + Convert.ToString(kv.Value)).Run();
                    DbAttribute a = DbAttribute.GetDbAttribute(kv.Key.ToUpperInvariant());
                    back[kv.Key.ToUpperInvariant()] = a == null ? null : e.GetAsString(a);
                }
                tx.EndTransaction();
                _pending++;
            }
            catch (Exception ex)
            {
                try { tx.AbortTransaction(); } catch { }
                Dictionary<string, object> f = Fail(ex.Message); f["rolled_back"] = true; return f;
            }
            Dictionary<string, object> r = Ok();
            r["name"] = e.GetAsString(ATT.FLNM); r["readback"] = back;
            return r;
        }

        private Dictionary<string, object> Undo(int steps)
        {
            int done = 0;
            for (int i = 0; i < Math.Min(steps, 20); i++) { UndoTransaction.PerformUndo(); done++; }
            _pending = Math.Max(0, _pending - done);
            Dictionary<string, object> r = Ok(); r["undone"] = done; return r;
        }

        private Dictionary<string, object> View(string name)
        {
            DbElement e = Get(name);
            string cmd = "AUTO " + e.GetAsString(ATT.FLNM); // [TESTAR-E3D] enquadra a vista 3D corrente
            PmlCommand.CreateCommand(cmd).Run();
            Dictionary<string, object> r = Ok(); r["command"] = cmd; return r;
        }

        [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr h, out RECT r);
        [StructLayout(LayoutKind.Sequential)] private struct RECT { public int L, T, R, B; }

        private Dictionary<string, object> Screenshot()
        {
            IntPtr h = Process.GetCurrentProcess().MainWindowHandle;
            RECT rc;
            if (h == IntPtr.Zero || !GetWindowRect(h, out rc)) return Fail("janela principal do E3D não encontrada");
            using (Bitmap bmp = new Bitmap(Math.Max(1, rc.R - rc.L), Math.Max(1, rc.B - rc.T)))
            {
                using (Graphics g = Graphics.FromImage(bmp)) g.CopyFromScreen(rc.L, rc.T, 0, 0, bmp.Size);
                using (MemoryStream ms = new MemoryStream())
                {
                    bmp.Save(ms, ImageFormat.Png);
                    Dictionary<string, object> r = Ok(); r["png_base64"] = Convert.ToBase64String(ms.ToArray()); return r;
                }
            }
        }

        private Dictionary<string, object> SaveWork(Dictionary<string, object> p)
        {
            if (S(p, "confirm") != "SAVEWORK") return Fail("SAVEWORK exige confirm=SAVEWORK");
            MDB.CurrentMDB.SaveWork(S(p, "comment") ?? "E3D Live MCP");
            _pending = 0;
            Dictionary<string, object> r = Ok(); r["saved"] = true; return r;
        }

        // ------------------------------------------------------------ utilidades

        private static DbElement Get(string name)
        {
            DbElement e = (string.IsNullOrEmpty(name) || name.Equals("CE", StringComparison.OrdinalIgnoreCase))
                ? CurrentElement.Element : DbElement.GetElement(name);
            if (e == null || !e.IsValid || e.IsNull) throw new ArgumentException("(2,109) elemento não encontrado: " + name);
            return e;
        }

        private static DbElementType TypeOf(string t)
        {
            DbElementType et = DbElementType.GetElementType(t.ToUpperInvariant());
            if (et == null) throw new ArgumentException("tipo de elemento desconhecido: " + t);
            return et;
        }

        private static bool TypeMatches(DbElement e, string t)
        {
            DbElementType et = e.ElementType;
            string u = t.ToUpperInvariant();
            return et.ShortName.Equals(u, StringComparison.OrdinalIgnoreCase) || et.Name.Equals(u, StringComparison.OrdinalIgnoreCase);
        }

        private static Dictionary<string, object> ReadAttrs(DbElement e, string[] names)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            foreach (string raw in names)
            {
                string n = raw.ToUpperInvariant();
                try
                {
                    if (n == "NAME") { d[n] = e.GetAsString(ATT.FLNM); continue; }
                    if (n == "TYPE") { d[n] = e.ElementType.ShortName; continue; }
                    if (n == "OWNER") { d[n] = e.Owner.IsValid ? e.Owner.GetAsString(ATT.FLNM) : null; continue; }
                    DbAttribute a = DbAttribute.GetDbAttribute(n);
                    if (a != null && e.IsAttributeValid(a)) d[n] = e.GetAsString(a);
                    else d[n] = Eval(e, n); // pseudo-atributos (ex. ABOR, MTOTUBE)
                }
                catch { /* atributo não aplicável a este tipo */ }
            }
            return d;
        }

        private static string Eval(DbElement e, string expr)
        {
            try { return e.EvaluateString(DbExpression.Parse(expr)); } catch { return null; }
        }

        private static string RefOf(DbElement e)
        {
            int[] r = e.Ref;
            return "=" + r[0] + "/" + r[1];
        }

        private static string NameOfRef(string refText)
        {
            try { return DbElement.GetElement(refText).GetAsString(ATT.FLNM); } catch { return refText; }
        }

        private static bool IsNull(Dictionary<string, object> d, string k)
        {
            object v;
            if (!d.TryGetValue(k, out v) || v == null) return true;
            string s = v.ToString().Trim().ToUpperInvariant();
            return s == "" || s == "NULREF" || s == "=0/0" || s == "UNSET";
        }

        private static bool FixedEquals(string a, string b)
        {
            if (a == null || b == null || a.Length != b.Length) return false;
            int diff = 0;
            for (int i = 0; i < a.Length; i++) diff |= a[i] ^ b[i];
            return diff == 0;
        }

        private static Dictionary<string, object> Ok() { Dictionary<string, object> d = new Dictionary<string, object>(); d["ok"] = true; return d; }
        private static Dictionary<string, object> Fail(string m) { Dictionary<string, object> d = new Dictionary<string, object>(); d["ok"] = false; d["error"] = m; return d; }
        private static string S(Dictionary<string, object> p, string k) { object v; return p.TryGetValue(k, out v) && v != null ? Convert.ToString(v) : null; }
        private static int I(Dictionary<string, object> p, string k, int def) { object v; return p.TryGetValue(k, out v) && v != null ? Convert.ToInt32(v) : def; }
        private static List<string> L(Dictionary<string, object> p, string k)
        {
            List<string> l = new List<string>();
            object v;
            if (p.TryGetValue(k, out v) && v is IEnumerable && !(v is string))
                foreach (object o in (IEnumerable)v) if (o != null) l.Add(o.ToString());
            return l;
        }
    }
}
