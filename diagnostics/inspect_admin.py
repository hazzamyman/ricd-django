# diagnostics/inspect_admin.py
from django import setup
from django.conf import settings
setup()
from django.contrib import admin
for model, ma in admin.site._registry.items():
    print("Model:", model, "Admin:", type(ma))
    try:
        inlines = getattr(ma, "inlines", ())
        for i in inlines:
            print("  Inline:", i, "is class?" , isinstance(i, type))
    except Exception as e:
        print("  error inspecting inlines:", e)