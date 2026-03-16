PREFIXES = """
PREFIX cg: <http://codegraph.dev/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# --- Index page queries ---

PROJECT_STATS = PREFIXES + """
SELECT
  (COUNT(DISTINCT ?f) AS ?fileCount)
  (COUNT(DISTINCT ?fn) AS ?functionCount)
  (COUNT(DISTINCT ?cl) AS ?classCount)
  (COUNT(DISTINCT ?fd) AS ?fieldCount)
WHERE {
  OPTIONAL { ?f a cg:File . }
  OPTIONAL { ?fn a cg:Function . }
  OPTIONAL { ?cl a cg:Class . }
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
SELECT ?module ?filePath
WHERE {
  ?module a cg:Module ;
          cg:filePath ?filePath .
}
ORDER BY ?filePath
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
  ?cls a cg:Class ;
       cg:name ?name ;
       cg:filePath ?filePath .
  OPTIONAL { ?cls cg:language ?language . }
  OPTIONAL { ?cls cg:lineNumber ?lineNumber . }
}
ORDER BY ?name
"""

CLASS_INHERITANCE = PREFIXES + """
SELECT ?cls ?parent
WHERE {
  ?cls a cg:Class ;
       cg:inherits ?parent .
}
"""

CLASS_INTERFACES = PREFIXES + """
SELECT ?cls ?iface
WHERE {
  ?cls a cg:Class ;
       cg:implements ?iface .
}
"""

CLASS_MIXINS = PREFIXES + """
SELECT ?cls ?mixin
WHERE {
  ?cls a cg:Class ;
       cg:mixes ?mixin .
}
"""

CLASS_FIELDS = PREFIXES + """
SELECT ?cls ?fieldName ?fieldType ?visibility ?mutability ?defaultValue
WHERE {
  ?cls a cg:Class ;
       cg:hasField ?field .
  ?field cg:name ?fieldName .
  OPTIONAL { ?field cg:type ?fieldType . }
  OPTIONAL { ?field cg:visibility ?visibility . }
  OPTIONAL { ?field cg:mutability ?mutability . }
  OPTIONAL { ?field cg:defaultValue ?defaultValue . }
}
ORDER BY ?cls ?fieldName
"""

CLASS_METHODS = PREFIXES + """
SELECT ?cls ?methodName ?returnType ?lineNumber
WHERE {
  ?cls a cg:Class ;
       cg:hasMethod ?method .
  ?method cg:name ?methodName .
  OPTIONAL { ?method cg:returnType ?returnType . }
  OPTIONAL { ?method cg:lineNumber ?lineNumber . }
}
ORDER BY ?cls ?methodName
"""

METHOD_PARAMETERS = PREFIXES + """
SELECT ?method ?paramName ?paramType
WHERE {
  ?method cg:hasParameter ?param .
  ?param cg:name ?paramName .
  OPTIONAL { ?param cg:type ?paramType . }
}
ORDER BY ?method ?paramName
"""

CLASS_CALLERS = PREFIXES + """
SELECT ?caller ?callerName ?callerType
WHERE {
  ?caller cg:calls ?method .
  ?method cg:belongsTo ?cls .
  ?cls a cg:Class ;
       cg:name ?clsName .
  FILTER(?clsName = ?targetName)
  ?caller cg:name ?callerName .
  ?caller a ?callerType .
}
"""

CLASS_DEPENDENCIES = PREFIXES + """
SELECT DISTINCT ?cls ?dep ?depName
WHERE {
  ?cls a cg:Class .
  ?cls cg:hasMethod ?method .
  ?method cg:calls ?depNode .
  ?depNode cg:belongsTo ?dep .
  ?dep a cg:Class ;
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
      cg:name ?name ;
      cg:filePath ?filePath .
  OPTIONAL { ?fn cg:language ?language . }
  OPTIONAL { ?fn cg:lineNumber ?lineNumber . }
  OPTIONAL { ?fn cg:belongsTo ?module . }
  FILTER NOT EXISTS { ?cls a cg:Class ; cg:hasMethod ?fn . }
}
ORDER BY ?name
"""

FUNCTION_PARAMETERS = PREFIXES + """
SELECT ?fn ?paramName ?paramType
WHERE {
  ?fn a cg:Function ;
      cg:hasParameter ?param .
  ?param cg:name ?paramName .
  OPTIONAL { ?param cg:type ?paramType . }
}
ORDER BY ?fn ?paramName
"""

FUNCTION_LOCAL_VARS = PREFIXES + """
SELECT ?fn ?varName ?varType ?mutability
WHERE {
  ?fn a cg:Function ;
      cg:hasLocalVar ?var .
  ?var cg:name ?varName .
  OPTIONAL { ?var cg:type ?varType . }
  OPTIONAL { ?var cg:mutability ?mutability . }
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
SELECT ?module ?name ?filePath
WHERE {
  ?module a cg:Module ;
          cg:name ?name ;
          cg:filePath ?filePath .
}
ORDER BY ?name
"""

MODULE_CLASSES = PREFIXES + """
SELECT ?module ?cls ?clsName
WHERE {
  ?cls a cg:Class ;
       cg:name ?clsName ;
       cg:belongsTo ?module .
}
ORDER BY ?module ?clsName
"""

MODULE_FUNCTIONS = PREFIXES + """
SELECT ?module ?fn ?fnName
WHERE {
  ?fn a cg:Function ;
      cg:name ?fnName ;
      cg:belongsTo ?module .
  FILTER NOT EXISTS { ?cls a cg:Class ; cg:hasMethod ?fn . }
}
ORDER BY ?module ?fnName
"""

MODULE_CONSTANTS = PREFIXES + """
SELECT ?module ?constName ?constValue ?constType
WHERE {
  ?module a cg:Module .
  ?const a cg:Constant ;
         cg:name ?constName ;
         cg:belongsTo ?module .
  OPTIONAL { ?const cg:value ?constValue . }
  OPTIONAL { ?const cg:type ?constType . }
}
ORDER BY ?module ?constName
"""

MODULE_IMPORTS = PREFIXES + """
SELECT ?module ?importTarget
WHERE {
  ?module a cg:Module ;
          cg:imports ?importTarget .
}
ORDER BY ?module ?importTarget
"""
