import os
import shutil
import argparse
import datetime

def create_archive_dir():
    """Crea una directory per archiviare i file vecchi."""
    archive_dir = os.path.join(os.getcwd(), "data", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    return archive_dir

def move_to_archive(file_path, archive_dir):
    """Sposta un file nella directory di archivio."""
    if not os.path.exists(file_path):
        print(f"File non trovato: {file_path}")
        return False
    
    filename = os.path.basename(file_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{filename}.{timestamp}.old"
    destination = os.path.join(archive_dir, new_filename)
    
    shutil.move(file_path, destination)
    print(f"File spostato in archivio: {file_path} -> {destination}")
    return True

def clean_json_files(data_dir, archive=True, delete=False):
    """Pulisce i vecchi file JSON."""
    json_files = [
        os.path.join(data_dir, "documents.json"),
        os.path.join(data_dir, "documents.json.bak")
    ]
    
    # Trova anche i backup automatici
    for file in os.listdir(data_dir):
        if file.startswith("documents.json.bak.") and file.endswith(".old") == False:
            json_files.append(os.path.join(data_dir, file))
    
    archive_dir = create_archive_dir() if archive else None
    
    for file in json_files:
        if os.path.exists(file):
            if archive:
                move_to_archive(file, archive_dir)
            elif delete:
                os.remove(file)
                print(f"File eliminato: {file}")
            else:
                print(f"File trovato (nessuna azione): {file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pulisce i vecchi file JSON dopo la migrazione a SQLite.")
    parser.add_argument("--data-dir", default="./data", help="Directory contenente i dati")
    parser.add_argument("--delete", action="store_true", help="Elimina i file invece di archiviarli")
    parser.add_argument("--no-archive", action="store_true", help="Non archiviare i file (solo se --delete non è specificato)")
    
    args = parser.parse_args()
    
    clean_json_files(
        args.data_dir, 
        archive=(not args.no_archive and not args.delete),
        delete=args.delete
    )
