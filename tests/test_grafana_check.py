import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "grafana-check.sh"


class GrafanaCheckTest(unittest.TestCase):
    def test_uses_service_account_token_as_bearer_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            args_path = tmp_path / "curl-args"
            curl_path = tmp_path / "curl"
            curl_path.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf '%s\\0' \"$@\" >> \"$CURL_ARGS_FILE\"\n"
                "case \"${!#}\" in\n"
                "  */api/health) printf '%s\\n' '{\"database\":\"ok\"}' ;;\n"
                "  */api/v1/rules) printf '%s\\n' '{\"data\":{\"groups\":[]}}' ;;\n"
                "  */api/v2/silences) printf '%s\\n' '[]' ;;\n"
                "  *) exit 1 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            curl_path.chmod(0o755)
            env = os.environ | {
                "PATH": "{}:{}".format(tmp_path, os.environ["PATH"]),
                "CURL_ARGS_FILE": str(args_path),
                "GRAFANA": "https://grafana.example",
                "GRAFANA_TOKEN": "test-service-token",
            }

            result = subprocess.run(
                ["bash", str(SCRIPT_PATH)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            args = [
                value.decode("utf-8")
                for value in args_path.read_bytes().split(b"\0")
                if value
            ]
            self.assertEqual(args.count("Authorization: Bearer test-service-token"), 3)
            self.assertEqual(args.count("-fsS"), 3)
            self.assertNotIn("-u", args)


if __name__ == "__main__":
    unittest.main()
