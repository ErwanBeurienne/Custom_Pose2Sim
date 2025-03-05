import os
import pytz
import ffmpeg
import shutil
import pandas as pd
from datetime import datetime


def import_log_test(log_test_path):
    """ function doc """
    
    # Load log test file
    test_log_file_df = pd.read_excel(
        log_test_path,
        header = 0,
        usecols = ["Groups", "Trials", "Date", "Time", "Athlete ID"],
        dtype ={"Athlete ID": str}
        )
    
    return test_log_file_df


def create_folder_structure(batch_path, trial_name=None):
    """Crée la structure de dossiers pour une BatchSession et un essai."""

    os.makedirs(batch_path, exist_ok=True)

    if trial_name:
        trial_path = os.path.join(batch_path, trial_name)
        os.makedirs(trial_path, exist_ok=True)
        
        return trial_path
    
    else:
        intrinsics_calibration_path = os.path.join(batch_path, "calibration", "intrinsics")
        os.makedirs(intrinsics_calibration_path, exist_ok=True)
        
        extrinsics_calibration_path = os.path.join(batch_path, "calibration", "extrinsics")
        os.makedirs(extrinsics_calibration_path, exist_ok=True)
        
        return intrinsics_calibration_path, extrinsics_calibration_path


def paste_config_file(folder_path):
    """Copie le fichier Config.toml (qui est dans le même dossier que ce script) vers le dossier spécifié."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))  
    source_config_path = os.path.join(script_dir, "Config.toml")

    if not os.path.exists(source_config_path):
        print(f"The file {source_config_path} doesn't exist!")
        return

    destination_config_path = os.path.join(folder_path, "Config.toml")
    shutil.copy(source_config_path, destination_config_path)


def convert_to_local_time(datetime_obj, target_timezone="America/Montreal", adjust_time=False):
    """Convertit un datetime naïf en heure locale (Montréal) avec possibilité d'adaptation de l'heure."""
    
    local_tz = pytz.timezone(target_timezone)
    
    datetime_local = local_tz.localize(datetime_obj)

    if adjust_time:
        utc_tz = pytz.utc
        datetime_obj_utc = utc_tz.localize(datetime_obj)  # Localiser l'heure naïve en UTC
        datetime_local = datetime_obj_utc.astimezone(local_tz)

    return datetime_local
    

def get_video_creation_time(video_path):
    """Récupère l'heure de création d'une vidéo"""
    
    try:
        probe = ffmpeg.probe(video_path, v='error', select_streams='v:0', show_entries='format_tags=creation_time') # Récupérer les informations sur la vidéo via ffmpeg
        creation_time_str = probe['format']['tags']['creation_time'] # Extraire la date de création
        creation_time = datetime.strptime(creation_time_str, '%Y-%m-%dT%H:%M:%S.%fZ') # Convertir en objet datetime

        return creation_time
    
    except ffmpeg.Error as e:
        print(f"Erreur ffmpeg: {e}")
        return None


def rename_video_extension(video_path):
    """Renomme l'extension d'un fichier vidéo en .mp4, peu importe la casse de l'extension d'origine."""
    
    new_video_name = os.path.splitext(video_path)[0] + ".mp4" # Crée le nouveau nom avec l'extension .mp4
    os.rename(video_path, new_video_name) # Renomme le fichier
    return new_video_name


def move_videos(source_folder, destination_folder, target_time, trial_type):
    """Déplace les vidéos des sous-dossiers des caméras vers le dossier de destination."""
    
    closest_time_diff = None
    target_time = convert_to_local_time(target_time)

    camera_folders = [f for f in os.listdir(source_folder) if "cam" in f.lower() and os.path.isdir(os.path.join(source_folder, f))]
    
    for camera_folder in camera_folders:
        camera_path = os.path.join(source_folder, camera_folder)
        video_files = [f for f in os.listdir(camera_path) if f.lower().endswith('.mp4')]
        closest_time_diff = None
        
        for video_file in video_files:
            video_path = os.path.join(camera_path, video_file)
            creation_time = get_video_creation_time(video_path)
            creation_time = convert_to_local_time(creation_time, adjust_time=True)
            time_diff = abs((creation_time - target_time).total_seconds())
            
            if closest_time_diff is None or time_diff < closest_time_diff:
                closest_time_diff = time_diff
                closest_video = video_path
        
        if closest_video:
            closest_video_renamed = rename_video_extension(closest_video)
            
            if trial_type == "calibration":
                destination_path = os.path.join(destination_folder, f"ext_{camera_folder}", f"ext_{camera_folder}.mp4")
            else:
                destination_path = os.path.join(destination_folder, "videos", f"{camera_folder}.mp4")
            
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy(closest_video_renamed, destination_path)
            print(f"Video {closest_video_renamed} moved to {destination_path}")


def organize_videos(excel_file_path, source_folder, destination_folder):
    """Organise les vidéos selon la structure demandée par Pose2Sim."""
    # Lire le fichier Excel
    test_log_file = import_log_test(excel_file_path)

    working_date = None

    for index, row in test_log_file.iterrows():

        trial_date = row["Date"].strftime("%Y-%m-%d")
        trial_type = row["Trials"]
        athlete_ID = row["Athlete ID"]
        trial_date_time = datetime.combine(row["Date"], row["Time"])

        if trial_date != working_date:
            working_date = trial_date
            base_path = os.path.join(destination_folder, f"Session_{trial_date}")
            os.makedirs(base_path, exist_ok=True)
            batch_counter = 1
            trial_counters = {}

        if trial_type == "calibration":
            batch_session = f"BatchSession_{batch_counter}"
            batch_path = os.path.join(base_path, batch_session)
            _, extrinsics_calibration_path = create_folder_structure(batch_path)
            
            paste_config_file(batch_path)
            move_videos(source_folder, extrinsics_calibration_path, trial_date_time, trial_type)
            
            batch_counter += 1
        
        else:
            trial_name = f"Trial_{athlete_ID}_{trial_counters.get(athlete_ID, 0) + 1}"
            trial_path = create_folder_structure(batch_path, trial_name)
            
            paste_config_file(trial_path)
            move_videos(source_folder, trial_path, trial_date_time, trial_type)

            trial_counters[athlete_ID] = trial_counters.get(athlete_ID, 0) + 1