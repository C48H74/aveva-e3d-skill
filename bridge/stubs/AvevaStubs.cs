// STUBS só para checar compilação fora do E3D. Assinaturas copiadas do cheatsheet
// verificado no E3D 3.1 (nhdang117/PMLNet.Learning). NÃO distribuir.
using System;
using System.Collections;
namespace Aveva.ApplicationFramework
{
    public class ServiceManager { }
    public interface IDependencyResolver { T GetImplementationOf<T>(); }
    public interface IAddin { string Name { get; } string Description { get; } void Start(ServiceManager s); void Stop(); }
    public interface IAddinInjected : IAddin { void Start(IDependencyResolver r); }
}
namespace Aveva.Core.Utilities.CommandLine
{
    public class Command { public static Command CreateCommand(string s) { return new Command(); } public bool Run() { return true; } }
}
namespace Aveva.Core.Utilities.Undo
{
    public class UndoTransaction
    {
        public static UndoTransaction GetUndoTransaction() { return new UndoTransaction(); }
        public void StartTransaction(string d) { } public void EndTransaction() { } public void AbortTransaction() { }
        public static void PerformUndo() { } public static void PerformRedo() { }
    }
}
namespace Aveva.Core.Database
{
    public enum DbType { Design, Catalog }
    public class DbAttribute { public static DbAttribute GetDbAttribute(string n) { return null; } }
    public class DbAttributeInstance { public static DbAttribute NAME, FLNM, POS, ORI, DESC; }
    public class DbElementType { public string Name; public string ShortName; public static DbElementType GetElementType(string n) { return null; } }
    public class DbExpression { public static DbExpression Parse(string s) { return null; } }
    public class DbElement
    {
        public static DbElement GetElement(string n) { return null; }
        public bool IsValid, IsNull; public DbElementType ElementType; public DbElement Owner; public int[] Ref;
        public DbElement[] Members() { return null; }
        public string GetAsString(DbAttribute a) { return null; }
        public bool IsAttributeValid(DbAttribute a) { return true; }
        public string EvaluateString(DbExpression e) { return null; }
        public void Claim() { }
    }
    public static class CurrentElement { public static DbElement Element; }
    public class MDB { public static MDB CurrentMDB; public string Name; public DbElement GetFirstWorld(DbType t) { return null; } public bool SaveWork(string c) { return true; } }
    public class Project { public static Project CurrentProject; public string Code, UserName; }
}
namespace Aveva.Core.Database.Filters
{
    using Aveva.Core.Database;
    public abstract class BaseFilter { }
    public class TrueFilter : BaseFilter { }
    public class TypeFilter : BaseFilter { public TypeFilter(DbElementType t) { } public TypeFilter(DbElementType[] t) { } }
    public class AndFilter : BaseFilter { public AndFilter(params BaseFilter[] f) { } }
    public class ExpressionFilter : BaseFilter { public ExpressionFilter(DbExpression e) { } }
    public class AttributeLikeFilter : BaseFilter { public AttributeLikeFilter(DbAttribute a, string p) { } }
    public class DBElementCollection : IEnumerable
    {
        public DBElementCollection(DbElement root, BaseFilter f) { } public bool IncludeRoot;
        public IEnumerator GetEnumerator() { return new DbElement[0].GetEnumerator(); }
    }
}
