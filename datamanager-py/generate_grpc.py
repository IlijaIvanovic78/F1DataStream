import subprocess
import sys
from pathlib import Path

def generate_grpc_stubs():


    script_dir = Path(__file__).parent

    proto_file = script_dir.parent / "telemetry.proto"
    output_dir = script_dir / "gen"
    
    output_dir.mkdir(exist_ok=True)
    
    if not proto_file.exists():
        print(f"Error: Proto file not found at {proto_file}")
        return False
    
    print(f"Generating gRPC stubs from {proto_file}")
    print(f"Output directory: {output_dir}")
    

    # python -m grpc_tools.protoc \
    # --proto_path=../ \
    # --python_out=gen/ \
    # --grpc_python_out=gen/ \
    # telemetry.proto
    try:
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={proto_file.parent}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            str(proto_file.name)
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error generating stubs: {result.stderr}")
            return False
        
        print("gRPC stubs generated successfully!")
        
        init_file = output_dir / "__init__.py"
        with open(init_file, 'w') as f:
            f.write('"""Generated gRPC stubs for telemetry service"""\n')
        
        print(f"Created {init_file}")
        
        generated_files = list(output_dir.glob("*.py"))
        print("\nGenerated files:")
        for file in generated_files:
            print(f"  - {file.name}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = generate_grpc_stubs()
    sys.exit(0 if success else 1)