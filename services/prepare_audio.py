"""python -m services.prepare_audio --check | --scripts audio/demo-scripts.json"""
import argparse
import hashlib
import json
from pathlib import Path

from config import DATA_DIR
from rag.search import get_poi_context
from services.content import has_source, is_placeholder
from services.tts import get_audio_result, text_hash, validate_language, write_metadata


def check_data():
    pois = json.loads((Path(DATA_DIR) / "pois.json").read_text(encoding="utf-8"))
    ready = 0
    for poi in pois:
        valid = has_source(poi.get("source")) and not is_placeholder(poi.get("description_vi"))
        ready += int(valid)
        print(f"{poi['id']}: {'READY' if valid else 'NEEDS CONTENT / SOURCE'}")
    print(f"{ready}/{len(pois)} POI ready. Five-language demo needs approved scripts in vi/en/ko/ja/zh.")
    return 0 if ready == len(pois) and ready else 1


def validate_script(script):
    validate_language(script.get("lang"))
    if script.get("approved") is not True or not has_source(script.get("source")):
        raise ValueError("Each script needs approved=true and an http(s) source.")
    text = script.get("text", "")
    if is_placeholder(text) or not 80 <= len(text) <= 6000:
        raise ValueError("Provide 80–6000 characters of reviewed narration, not placeholder text.")
    if not get_poi_context(script.get("poi_id"), script["lang"]):
        raise ValueError("Unknown POI id.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--scripts", type=Path)
    args = parser.parse_args()
    if not args.scripts:
        return check_data()
    scripts = json.loads(args.scripts.read_text(encoding="utf-8-sig"))
    if not isinstance(scripts, list) or not scripts:
        parser.error("Scripts must be a non-empty JSON array.")
    # Validate the entire input before making any network calls.
    seen = set()
    for index, script in enumerate(scripts, 1):
        try:
            if not isinstance(script, dict):
                raise ValueError("Script must be a JSON object.")
            validate_script(script)
        except (ValueError, TypeError) as error:
            parser.error(f"Script {index}: {error}")
        key = (script["poi_id"], script["lang"])
        if key in seen:
            parser.error(f"Duplicate script: {key}")
        seen.add(key)
    if args.check:
        print(f"{len(scripts)} approved scripts ready; no audio generated.")
        return 0
    failures = 0
    for script in scripts:
        result = get_audio_result(script["poi_id"], script["lang"], script["text"])
        if not result["audio_path"]:
            failures += 1
            print(f"FAILED {script['poi_id']}/{script['lang']}: {result.get('warning')}")
            continue
        path = Path(result["audio_path"])
        write_metadata(path, {"text": script["text"], "text_sha256": text_hash(script["text"]),
                              "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "lang": script["lang"], "provider": result["tts_provider"],
                              "source": script["source"], "approved": True, "prepared": True,
                              "context_sha256": text_hash(get_poi_context(script["poi_id"], script["lang"]))})
        print(f"READY {path.name} ({result['tts_provider']})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
