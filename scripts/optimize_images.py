import os
import sys
import argparse
import hashlib
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image, ImageOps

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DEFAULT_IGNORE_DIRS = {"base", "partners", "orgs", "favicon"}
DEFAULT_SIZES = {"sm": 600, "md": 1200, "hd": 1920}
TARGET_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png"}
CACHE_FILE = Path(".image_cache.json")

def load_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

def should_skip_file(file_path: Path) -> bool:
    stem = file_path.stem
    for suffix in ["-sm", "-md", "-hd", "-lg", "-thumb"]:
        if stem.endswith(suffix):
            return True
    return False

def resize_image(img: Image.Image, max_dim: int) -> Image.Image:
    width, height = img.size
    if width <= max_dim and height <= max_dim:
        return img.copy()

    if width > height:
        new_width = max_dim
        new_height = int(round(height * (max_dim / width)))
    else:
        new_height = max_dim
        new_width = int(round(width * (max_dim / height)))

    return img.resize((new_width, new_height), resample=Image.Resampling.LANCZOS)

def process_file_worker(args_tuple):
    file_path_str, sizes, quality, force, dry_run, cached_hash = args_tuple
    file_path = Path(file_path_str)

    if should_skip_file(file_path):
        return file_path_str, None, 0, 0, 0, None

    src_size = file_path.stat().st_size

    output_specs = []
    if file_path.suffix.lower() != ".webp":
        output_specs.append(("original", None, file_path.with_suffix(".webp")))
    output_specs.extend(
        (label, max_dim, file_path.with_name(f"{file_path.stem}-{label}.webp"))
        for label, max_dim in sizes.items()
    )

    all_exist = all(out_path.exists() for _, _, out_path in output_specs)

    current_hash = None
    if not force and all_exist:
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        current_hash = h.hexdigest()
        
        if current_hash == cached_hash:
            if not dry_run and file_path.suffix.lower() != ".webp":
                file_path.unlink()
            return file_path_str, current_hash, 0, 1, 0, None

    if current_hash is None:
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        current_hash = h.hexdigest()

    try:
        with Image.open(file_path) as raw_img:
            img = ImageOps.exif_transpose(raw_img)
            orig_w, orig_h = img.size

            created = 0
            msg_list = []
            for label, max_dim, out_path in output_specs:
                if dry_run:
                    size_description = "original size" if max_dim is None else f"max {max_dim}px"
                    msg_list.append(f"  [DRY-RUN] {file_path.name} -> {out_path.name} ({size_description})")
                    created += 1
                    continue

                if max_dim is None or (orig_w <= max_dim and orig_h <= max_dim):
                    resized = img.copy()
                else:
                    resized = resize_image(img, max_dim)
                
                if resized.mode in ("RGBA", "LA") or (resized.mode == "P" and "transparency" in resized.info):
                    save_img = resized.convert("RGBA")
                else:
                    save_img = resized.convert("RGB")

                save_img.save(out_path, format="WEBP", quality=quality, method=6)
                out_size = out_path.stat().st_size
                savings = (1 - (out_size / src_size)) * 100 if src_size > 0 else 0
                msg_list.append(f"  [OK] {file_path.name} -> {out_path.name} [{save_img.width}x{save_img.height}, {out_size // 1024} KB, -{savings:.1f}%]")
                created += 1

            if not dry_run and file_path.suffix.lower() != ".webp":
                file_path.unlink()
                msg_list.append(f"  [DELETED] {file_path.name}")

            return file_path_str, current_hash, created, 0, 0, "\n".join(msg_list)
    except Exception as e:
        return file_path_str, None, 0, 0, 0, f"  [ERR] Chyba při zpracování {file_path}: {e}"

def optimize_directory(base_dir: Path, sizes: dict, quality: int, force: bool, dry_run: bool, ignore_dirs: set, workers: int = None):
    if workers is None:
        workers = os.cpu_count() or 4

    print(f"Skenuji složku: {base_dir}")
    print(f"Velikosti k vygenerování: {', '.join(f'{k}={v}px' for k, v in sizes.items())}")
    print(f"WebP kvalita: {quality}")
    print(f"Paralelní vlákna: {workers}")
    if dry_run:
        print("Režim DRY-RUN (žádné soubory nebudou zapsány)\n")
    else:
        print()

    cache = load_cache()

    files_to_process = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in TARGET_EXTENSIONS and not should_skip_file(p):
                files_to_process.append(p)

    total_files = len(files_to_process)
    print(f"Nalezeno {total_files} kandidátů ke kontrole. Spouštím optimalizaci...\n")

    tasks = [(str(p), sizes, quality, force, dry_run, cache.get(str(p))) for p in files_to_process]

    total_created = 0
    total_skipped = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_file_worker, t): t[0] for t in tasks}
        for future in as_completed(futures):
            file_path_str, new_hash, created, skipped, _, msg = future.result()
            total_created += created
            total_skipped += skipped
            if new_hash and not dry_run:
                cache[file_path_str] = new_hash
            if msg:
                print(msg, flush=True)

    if not dry_run:
        save_cache(cache)

    print("\n" + "=" * 50)
    print("Dokončeno!")
    print(f"Celkem zkontrolováno souborů: {total_files}")
    print(f"Nově vygenerováno / aktualizováno variant: {total_created}")
    print(f"Přeskočeno (již aktuální): {total_skipped}")
    print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Optimalizátor obrázků pro Zvaž vědu!")
    parser.add_argument("--dir", type=str, default="static/media/imgs", help="Cílová složka")
    parser.add_argument("--quality", type=int, default=85, help="WebP kvalita")
    parser.add_argument("--workers", type=int, default=None, help="Počet procesů")
    parser.add_argument("--force", action="store_true", help="Vynutit přegenerování")
    parser.add_argument("--dry-run", action="store_true", help="Pouze zobrazí")
    parser.add_argument("--include-all-dirs", action="store_true", help="Včetně log")

    args = parser.parse_args()

    target_dir = Path(args.dir)
    if not target_dir.exists():
        print(f"Chyba: Složka '{target_dir}' neexistuje.", file=sys.stderr)
        sys.exit(1)

    ignore_dirs = set() if args.include_all_dirs else DEFAULT_IGNORE_DIRS

    optimize_directory(
        base_dir=target_dir,
        sizes=DEFAULT_SIZES,
        quality=args.quality,
        force=args.force,
        dry_run=args.dry_run,
        ignore_dirs=ignore_dirs,
        workers=args.workers
    )

if __name__ == "__main__":
    main()
