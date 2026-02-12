import langfuse
print("Attributes in langfuse:", dir(langfuse))
try:
    from langfuse.decorators import langfuse_context, observe
    print("langfuse.decorators found")
except ImportError:
    print("langfuse.decorators NOT found")

try:
    from langfuse import observe, langfuse_context
    print("observe and langfuse_context found in langfuse top level")
except ImportError:
    print("observe or langfuse_context NOT found in langfuse top level")

try:
    from langfuse import propagate_attributes
    print("propagate_attributes found in langfuse top level")
except ImportError:
    print("propagate_attributes NOT found")
