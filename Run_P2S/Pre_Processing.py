import os
import sys
import ffmpeg
import shutil
import pandas as pd
from datetime import datetime


def import_log_test(log_test_path):
    """ function doc """
    
    # Load log test file
    test_log_file_df = pd.read_excel(
        log_test_path,
        header=0,
        usecols=["Groups", "Trials", "Date", "Time", "Jump time", "Athlete name"]
        )
    
    return test_log_file_df


def create_folder_structure(base_path, batch_session, trial_name=None):
    """Crée la structure de dossiers pour une BatchSession et un essai."""
    
    batch_path = os.path.join(base_path, batch_session)
    os.makedirs(batch_path, exist_ok=True)

    if trial_name:
        trial_path = os.path.join(batch_path, trial_name)
        os.makedirs(trial_path, exist_ok=True)
        videos_path = os.path.join(trial_path, "videos")
        os.makedirs(videos_path, exist_ok=True)
        return videos_path

    calibration_path = os.path.join(batch_path, "calibration")
    os.makedirs(calibration_path, exist_ok=True)
    return calibration_path


def paste_config_file(folder_path):
    """Copie le fichier Config.toml (qui est dans le même dossier que ce script) vers le dossier spécifié."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))  
    source_config_path = os.path.join(script_dir, "Config.toml")

    if not os.path.exists(source_config_path):
        print(f"The file {source_config_path} doesn't exist!")
        return

    destination_config_path = os.path.join(folder_path, "Config.toml")
    shutil.copy(source_config_path, destination_config_path)


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


def move_videos(source_folder, destination_folder, target_time):
    """Déplace les vidéos des sous-dossiers des caméras vers le dossier de destination."""
    closest_video = None
    closest_time_diff = None

    for camera_folder in os.listdir(source_folder):
        camera_path = os.path.join(source_folder, camera_folder)
        if os.path.isdir(camera_path):
            for video_file in os.listdir(camera_path):
                if video_file.endswith('.MP4'):
                    video_path = os.path.join(camera_path, video_file)
                    creation_time = get_video_creation_time(video_path)
                    time_diff = abs((creation_time - target_time).total_seconds())

                    if closest_time_diff is None or time_diff < closest_time_diff:
                        closest_time_diff = time_diff
                        closest_video = video_path

    if closest_video:
        closest_video_renamed = rename_video_extension(closest_video)
        shutil.move(closest_video_renamed, destination_folder)
        print(f"video moves - programme stopped manually")
        sys.exit()


def organize_videos(excel_file_path, source_folder, destination_folder):
    """Organise les vidéos selon la structure demandée par Pose2Sim."""
    # Lire le fichier Excel
    test_log_file = import_log_test(excel_file_path)

    current_date = None

    for index, row in test_log_file.iterrows():

        trial_date = row["Date"].strftime("%Y-%m-%d")
        trial_type = row["Trials"]
        trial_name = row["Athlete name"]
        trial_date_time = datetime.combine(row["Date"], row["Time"])

        if trial_date != current_date:
            current_date = trial_date
            base_path = os.path.join(destination_folder, f"Session_{trial_date}")
            os.makedirs(base_path, exist_ok=True)
            batch_counter = 1
            trial_counters = {}

        if trial_type == "calibration":
            batch_session = f"BatchSession_{batch_counter}"
            calibration_path = create_folder_structure(base_path, batch_session)
            paste_config_file(calibration_path)
            move_videos(source_folder, calibration_path, trial_date_time)
            batch_counter += 1
        else:
            trial_name = f"Trial_{trial_name}_{trial_counters.get(trial_name, 0) + 1}"
            videos_path = create_folder_structure(base_path, batch_session, trial_name)
            paste_config_file(videos_path)
            move_videos(source_folder, videos_path, trial_date_time)
            trial_counters[trial_name] = trial_counters.get(trial_name, 0) + 1