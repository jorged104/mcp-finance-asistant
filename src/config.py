import yaml
import os
from dotenv import load_dotenv


def load_config(path="config.yaml",  env_path=".env"):
    load_dotenv(dotenv_path=env_path)

    with open(path, "r") as f:
        raw = yaml.safe_load(f)
        

        # Reemplazar variables de entorno (por si hay ${VAR})
        
        def resolve_env(val):
            if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
                return os.getenv(val[2:-1])

            return val

        resolved = {
            section: {k: resolve_env(v) for k, v in section_data.items()}
            for section, section_data in raw.items()
        }

        return resolved
