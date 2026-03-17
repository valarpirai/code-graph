PREFIXES = """
PREFIX cg: <http://codegraph.dev/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# All TypeDefinition subtypes (rdflib SPARQL has no subclass inference)
_TYPE_DEF_VALUES = "cg:Class cg:AbstractClass cg:DataClass cg:Interface cg:Enum cg:Struct cg:Trait cg:Mixin"
# All Callable subtypes
_CALLABLE_VALUES = "cg:Function cg:Method cg:Constructor"
# Standalone function only
_FUNCTION_VALUE = "cg:Function"
# StorageNode subtypes used for module constants
_STORAGE_VALUES = "cg:Field cg:Constant cg:LocalVariable"

# --- Index page queries ---

PROJECT_STATS = PREFIXES + """
SELECT
  (COUNT(DISTINCT ?f) AS ?fileCount)
  (COUNT(DISTINCT ?fn) AS ?functionCount)
  (COUNT(DISTINCT ?cl) AS ?classCount)
  (COUNT(DISTINCT ?fd) AS ?fieldCount)
WHERE {
  OPTIONAL { ?f a cg:File . }
  OPTIONAL {
    ?fn a ?fnType .
    VALUES ?fnType { """ + _CALLABLE_VALUES + """ }
  }
  OPTIONAL {
    ?cl a ?clType .
    VALUES ?clType { """ + _TYPE_DEF_VALUES + """ }
  }
  OPTIONAL { ?fd a cg:Field . }
}
"""

PROJECT_LANGUAGES = PREFIXES + """
SELECT DISTINCT ?language
WHERE {
  ?f a cg:File ;
     cg:language ?language .
}
ORDER BY ?language
"""

TOP_LEVEL_MODULES = PREFIXES + """
SELECT ?module ?name
WHERE {
  ?module a cg:Module ;
          cg:name ?name .
}
ORDER BY ?name
"""

CLUSTER_SUMMARY = PREFIXES + """
SELECT ?cluster ?cohesionScore ?topNode
WHERE {
  ?cluster a cg:Cluster ;
           cg:cohesionScore ?cohesionScore .
  OPTIONAL {
    ?cluster cg:hasNode ?topNode .
  }
}
ORDER BY DESC(?cohesionScore)
"""

# --- Class page queries ---

CLASS_DETAILS = PREFIXES + """
SELECT ?cls ?name ?filePath ?language ?lineNumber
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:name ?name .
  OPTIONAL { ?file a cg:File ; cg:defines ?cls ; cg:filePath ?filePath ; cg:language ?language . }
  OPTIONAL { ?cls cg:line ?lineNumber . }
}
ORDER BY ?name
"""

CLASS_INHERITANCE = PREFIXES + """
SELECT ?cls ?parent
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:inherits ?parent .
}
"""

CLASS_INTERFACES = PREFIXES + """
SELECT ?cls ?iface
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:implements ?iface .
}
"""

CLASS_MIXINS = PREFIXES + """
SELECT ?cls ?mixin
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:mixes ?mixin .
}
"""

CLASS_FIELDS = PREFIXES + """
SELECT ?cls ?fieldName ?fieldType ?visibility ?defaultValue
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:hasField ?field .
  ?field cg:name ?fieldName .
  OPTIONAL { ?field cg:dataType ?fieldType . }
  OPTIONAL { ?field cg:visibility ?visibility . }
  OPTIONAL { ?field cg:value ?defaultValue . }
}
ORDER BY ?cls ?fieldName
"""

CLASS_METHODS = PREFIXES + """
SELECT ?cls ?methodName ?returnType ?lineNumber
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:hasMethod ?method .
  ?method cg:name ?methodName .
  OPTIONAL { ?method cg:returnType ?returnType . }
  OPTIONAL { ?method cg:line ?lineNumber . }
}
ORDER BY ?cls ?methodName
"""

METHOD_PARAMETERS = PREFIXES + """
SELECT ?method ?paramName ?paramType
WHERE {
  ?method cg:hasParameter ?param .
  ?param cg:name ?paramName .
  OPTIONAL { ?param cg:dataType ?paramType . }
}
ORDER BY ?method ?paramName
"""

CLASS_DEPENDENCIES = PREFIXES + """
SELECT DISTINCT ?cls ?dep ?depName
WHERE {
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:hasMethod ?method .
  ?method cg:calls ?depMethod .
  ?dep a ?depType .
  VALUES ?depType { """ + _TYPE_DEF_VALUES + """ }
  ?dep cg:hasMethod ?depMethod ;
       cg:name ?depName .
  FILTER(?dep != ?cls)
}
ORDER BY ?cls ?depName
"""

CLASS_CLUSTER = PREFIXES + """
SELECT ?cls ?cluster ?cohesionScore
WHERE {
  ?cluster a cg:Cluster ;
           cg:hasNode ?cls ;
           cg:cohesionScore ?cohesionScore .
}
"""

# --- Function page queries ---

STANDALONE_FUNCTIONS = PREFIXES + """
SELECT ?fn ?name ?filePath ?language ?lineNumber ?module
WHERE {
  ?fn a cg:Function ;
      cg:name ?name .
  OPTIONAL { ?file a cg:File ; cg:defines ?fn ; cg:filePath ?filePath ; cg:language ?language . }
  OPTIONAL { ?fn cg:line ?lineNumber . }
  OPTIONAL { ?module a cg:Module ; cg:containsFile ?file . ?file cg:defines ?fn . }
  FILTER NOT EXISTS {
    ?cls a ?clsType .
    VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
    ?cls cg:hasMethod ?fn .
  }
}
ORDER BY ?name
"""

FUNCTION_PARAMETERS = PREFIXES + """
SELECT ?fn ?paramName ?paramType
WHERE {
  ?fn a cg:Function ;
      cg:hasParameter ?param .
  ?param cg:name ?paramName .
  OPTIONAL { ?param cg:dataType ?paramType . }
}
ORDER BY ?fn ?paramName
"""

FUNCTION_LOCAL_VARS = PREFIXES + """
SELECT ?fn ?varName ?varType
WHERE {
  ?fn a cg:Function ;
      cg:defines ?var .
  ?var a cg:LocalVariable ;
       cg:name ?varName .
  OPTIONAL { ?var cg:dataType ?varType . }
}
ORDER BY ?fn ?varName
"""

FUNCTION_CALLERS = PREFIXES + """
SELECT ?fn ?caller ?callerName
WHERE {
  ?caller cg:calls ?fn .
  ?caller cg:name ?callerName .
}
"""

FUNCTION_CALLEES = PREFIXES + """
SELECT ?fn ?callee ?calleeName
WHERE {
  ?fn cg:calls ?callee .
  ?callee cg:name ?calleeName .
}
ORDER BY ?fn ?calleeName
"""

FUNCTION_FRAMEWORK_ROLE = PREFIXES + """
SELECT ?fn ?role ?entryPointScore
WHERE {
  ?fn a cg:Function .
  OPTIONAL { ?fn cg:frameworkRole ?role . }
  OPTIONAL { ?fn cg:entryPointScore ?entryPointScore . }
}
"""

FUNCTION_CLUSTER = PREFIXES + """
SELECT ?fn ?cluster ?cohesionScore
WHERE {
  ?cluster a cg:Cluster ;
           cg:hasNode ?fn ;
           cg:cohesionScore ?cohesionScore .
}
"""

# --- Module page queries ---

MODULE_DETAILS = PREFIXES + """
SELECT ?module ?name
WHERE {
  ?module a cg:Module ;
          cg:name ?name .
}
ORDER BY ?name
"""

MODULE_CLASSES = PREFIXES + """
SELECT ?module ?cls ?clsName
WHERE {
  ?module a cg:Module ;
          cg:containsFile ?file .
  ?file cg:defines ?cls .
  ?cls a ?clsType .
  VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
  ?cls cg:name ?clsName .
}
ORDER BY ?module ?clsName
"""

MODULE_FUNCTIONS = PREFIXES + """
SELECT ?module ?fn ?fnName
WHERE {
  ?module a cg:Module ;
          cg:containsFile ?file .
  ?file cg:defines ?fn .
  ?fn a cg:Function ;
      cg:name ?fnName .
  FILTER NOT EXISTS {
    ?cls a ?clsType .
    VALUES ?clsType { """ + _TYPE_DEF_VALUES + """ }
    ?cls cg:hasMethod ?fn .
  }
}
ORDER BY ?module ?fnName
"""

MODULE_CONSTANTS = PREFIXES + """
SELECT ?module ?constName ?constValue ?constType
WHERE {
  ?module a cg:Module ;
          cg:containsFile ?file .
  ?file cg:defines ?const .
  ?const a ?constType .
  VALUES ?constType { cg:Constant cg:Field cg:LocalVariable }
  ?const cg:name ?constName .
  OPTIONAL { ?const cg:value ?constValue . }
}
ORDER BY ?module ?constName
"""

MODULE_IMPORTS = PREFIXES + """
SELECT ?module ?importTarget
WHERE {
  ?module a cg:Module ;
          cg:containsFile ?file .
  ?file cg:imports ?importTarget .
}
ORDER BY ?module ?importTarget
"""
