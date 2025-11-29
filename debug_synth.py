"""
ASCII-only debugging script - No Unicode characters
"""
import sys
import traceback
import os
import json
from dotenv import load_dotenv

load_dotenv("local_setup/.env.local")

print("="*80)
print("DEBUGGING PYDANTIC VALIDATION ERROR")
print("="*80)

# Step 1: Import models
print("\n[STEP 1] Importing sunona.models...")
try:
    from sunona.models import Synthesizer
    print("[OK] Import successful")
except Exception as e:
    print("[FAIL] Import failed:")
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test Synthesizer with minimal config
print("\n[STEP 2] Testing Synthesizer with provider='system'...")
print("Config: provider='system', stream=True, audio_format='wav'")

try:
    synth = Synthesizer(
        provider="system",
        stream=True,
        audio_format="wav"
    )
    print("[OK] Synthesizer created successfully!")
    print(f"     Provider: {synth.provider}")
    print(f"     Config: {synth.provider_config}")
    print(f"     Stream: {synth.stream}")
except Exception as e:
    print("[FAIL] Synthesizer creation failed!")
    print(f"       Error type: {type(e).__name__}")
    print(f"       Error message: {str(e)}")
    
    # Try to extract Pydantic validation details
    if hasattr(e, 'errors'):
        print("\n[PYDANTIC VALIDATION ERRORS]")
        errors = e.errors()
        for i, err in enumerate(errors, 1):
            print(f"\n  Error #{i}:")
            print(f"    Location: {err.get('loc', 'N/A')}")
            print(f"    Type: {err.get('type', 'N/A')}")
            print(f"    Message: {err.get('msg', 'N/A')}")
            if 'input' in err:
                print(f"    Input value: {err.get('input')}")
            if 'ctx' in err:
                print(f"    Context: {err.get('ctx')}")
    
    print("\n[FULL TRACEBACK]")
    traceback.print_exc()
    
    # Write error to file for analysis
    with open("synth_error.txt", "w") as f:
        f.write(f"Error Type: {type(e).__name__}\n")
        f.write(f"Error Message: {str(e)}\n\n")
        if hasattr(e, 'errors'):
            f.write("Pydantic Errors:\n")
            f.write(json.dumps(e.errors(), indent=2))
        f.write("\n\nTraceback:\n")
        traceback.print_exc(file=f)
    
    print("\n[ERROR DETAILS SAVED TO: synth_error.txt]")
    sys.exit(1)

print("\n" + "="*80)
print("ALL TESTS PASSED")
print("="*80)
