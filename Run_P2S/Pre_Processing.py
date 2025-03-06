import os
import pytz
import ffmpeg
import shutil
import pandas as pd
from datetime import datetime
import logging
from typing import Tuple, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def get_last_two_components(path: str) -> str:
    """Get the last two components of a path.

    Args:
        path (str): The input path.

    Returns:
        str: The last two components of the path.
    """
    components = path.split(os.sep)
    last_2_components = os.sep.join(components[-2:])
    last_2_components = "../" + last_2_components
    return last_2_components


def import_log_test(log_test_path: str) -> pd.DataFrame:
    """Load the log test file from the specified path.

    Args:
        log_test_path (str): Path to the log test Excel file.

    Returns:
        pd.DataFrame: DataFrame containing the log test data.
    """
    try:
        # Read the Excel file and specify that 'Athlete ID' should be read as a string
        test_log_file_df = pd.read_excel(
            log_test_path,
            header=0,
            usecols=["Groups", "Trials", "Date", "Time", "Athlete ID"],
            dtype={"Athlete ID": str}
        )
        return test_log_file_df
    except Exception as e:
        logging.error(f"Error reading Excel file: {e}")
        raise

def create_folder_structure(batch_path: str, trial_name: Optional[str] = None) -> Union[str, Tuple[str, str]]:
    """Create the folder structure for a BatchSession and a trial.

    Args:
        batch_path (str): Path to the batch session folder.
        trial_name (Optional[str]): Name of the trial folder.

    Returns:
        Union[str, Tuple[str, str]]: Path to the trial folder or paths to the calibration folders.
    """
    # Create the batch session folder if it doesn't exist
    os.makedirs(batch_path, exist_ok=True)

    if trial_name:
        # Create the trial folder inside the batch session folder
        trial_path = os.path.join(batch_path, trial_name)
        os.makedirs(trial_path, exist_ok=True)
        return trial_path
    else:
        # Create the calibration folders inside the batch session folder
        intrinsics_calibration_path = os.path.join(batch_path, "calibration", "intrinsics")
        os.makedirs(intrinsics_calibration_path, exist_ok=True)
        
        extrinsics_calibration_path = os.path.join(batch_path, "calibration", "extrinsics")
        os.makedirs(extrinsics_calibration_path, exist_ok=True)
        
        return intrinsics_calibration_path, extrinsics_calibration_path

def paste_config_file(folder_path: str) -> None:
    """Copy the Config.toml file to the specified folder.

    Args:
        folder_path (str): Destination folder path.
    """
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))  
    # Path to the source Config.toml file
    source_config_path = os.path.join(script_dir, "Config.toml")

    if not os.path.exists(source_config_path):
        logging.warning(f"The file {source_config_path} doesn't exist!")
        return

    # Path to the destination Config.toml file
    destination_config_path = os.path.join(folder_path, "Config.toml")
    # Copy the Config.toml file to the destination folder
    shutil.copy(source_config_path, destination_config_path)

def convert_to_local_time(datetime_obj: datetime, target_timezone: str = "America/Montreal", adjust_time: bool = False) -> datetime:
    """Convert a naive datetime to local time (Montreal) with optional time adjustment.

    Args:
        datetime_obj (datetime): Naive datetime object.
        target_timezone (str): Target timezone.
        adjust_time (bool): Whether to adjust the time.

    Returns:
        datetime: Localized datetime object.
    """
    # Get the target timezone
    local_tz = pytz.timezone(target_timezone)
    # Localize the naive datetime object to the target timezone
    datetime_local = local_tz.localize(datetime_obj)

    if adjust_time:
        # Convert the naive datetime object to UTC and then to the target timezone
        utc_tz = pytz.utc
        datetime_obj_utc = utc_tz.localize(datetime_obj)
        datetime_local = datetime_obj_utc.astimezone(local_tz)

    return datetime_local

def get_video_creation_time(video_path: str) -> Optional[datetime]:
    """Get the creation time of a video.

    Args:
        video_path (str): Path to the video file.

    Returns:
        Optional[datetime]: Creation time of the video.
    """
    try:
        # Use ffmpeg to probe the video file and get the creation time
        probe = ffmpeg.probe(video_path, v='error', select_streams='v:0', show_entries='format_tags=creation_time')
        creation_time_str = probe['format']['tags']['creation_time']
        # Convert the creation time string to a datetime object
        creation_time = datetime.strptime(creation_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        return creation_time
    except ffmpeg.Error as e:
        logging.error(f"ffmpeg error: {e}")
        return None

def move_videos(source_folder: str, destination_folder: str, target_time: datetime, trial_type: str, trial_name: str) -> None:
    """Move videos from camera subfolders to the destination folder.

    Args:
        source_folder (str): Source folder path.
        destination_folder (str): Destination folder path.
        target_time (datetime): Target time for video selection.
        trial_type (str): Type of trial (e.g., "calibration").
        trial_name (str): Name of the trial.
    """
    # Convert the target time to local time
    target_time = convert_to_local_time(target_time)
    # Get the list of camera folders in the source folder
    camera_folders = [f for f in os.listdir(source_folder) if "cam" in f.lower() and os.path.isdir(os.path.join(source_folder, f))]

    for camera_folder in camera_folders:
        camera_path = os.path.join(source_folder, camera_folder)
        # Get the list of video files in the camera folder
        video_files = [f for f in os.listdir(camera_path) if f.lower().endswith('.mp4')]
        closest_time_diff = None
        closest_video = None

        for video_file in video_files:
            video_path = os.path.join(camera_path, video_file)
            # Get the creation time of the video
            creation_time = get_video_creation_time(video_path)
            if creation_time:
                # Convert the creation time to local time
                creation_time = convert_to_local_time(creation_time, adjust_time=True)
                # Calculate the time difference between the creation time and the target time
                time_diff = abs((creation_time - target_time).total_seconds())

                # Find the video with the closest creation time to the target time
                if closest_time_diff is None or time_diff < closest_time_diff:
                    closest_time_diff = time_diff
                    closest_video = video_path

        if closest_video:
            # Construct the new file name
            new_file_name = f"{target_time.strftime('%Y-%m-%d_%Hh%M')}_{trial_name}_{camera_folder}.mp4"
            new_video_path = os.path.join(camera_path, new_file_name)
            
            # Rename the video file in the origin folder
            os.rename(closest_video, new_video_path)
            
            # Determine the destination path based on the trial type
            if trial_type == "calibration":
                destination_path = os.path.join(destination_folder, f"ext_{camera_folder}")
            else:
                destination_path = os.path.join(destination_folder, "videos")

            # Create the destination folder if it doesn't exist
            os.makedirs(destination_path, exist_ok=True)
            
            # Copy the renamed video file to the destination folder
            shutil.copy(new_video_path, destination_path)

def add_intrinsics_videos(intrinsics_calibration_path: str, intrinsics_videos_path: str) -> None:
    """Add intrinsics calibration videos to the intrinsics calibration folder.

    Args:
        intrinsics_calibration_path (str): Path to the intrinsics calibration folder.
        intrinsics_videos_path (str): Path to the source folder containing intrinsics videos.
    """
    # Copy the entire directory of intrinsics videos to the intrinsics calibration folder
    if os.path.exists(intrinsics_videos_path):
        shutil.copytree(intrinsics_videos_path, intrinsics_calibration_path, dirs_exist_ok=True)
    else:
        logging.warning(f"The source folder {intrinsics_videos_path} does not exist!")

def organize_videos(excel_file_path: str, source_folder: str, destination_folder: str, intrinsics_videos_path: str) -> None:
    """Organize videos according to the structure required by Pose2Sim.

    Args:
        excel_file_path (str): Path to the Excel file containing the log test data.
        source_folder (str): Source folder path.
        destination_folder (str): Destination folder path.
        intrinsics_videos_path (str): Path to the source folder containing intrinsics videos.
    """
    # Import the log test data from the Excel file
    test_log_file = import_log_test(excel_file_path)

    current_date = None
    total_files = len(test_log_file)

    for index, row in test_log_file.iterrows():
        trial_date = row["Date"].strftime("%Y-%m-%d")
        trial_type = row["Trials"]
        athlete_ID = row["Athlete ID"]
        trial_date_time = datetime.combine(row["Date"], row["Time"])
        progress = (index + 1) / total_files * 100

        if trial_date != current_date:
            current_date = trial_date
            # Create the base path for the session
            base_path = os.path.join(destination_folder, f"Session_{trial_date}")
            os.makedirs(base_path, exist_ok=True)
            batch_counter = 1
            trial_counters = {}

        if trial_type == "calibration":
            # Create the folder structure for a calibration batch session
            batch_session = f"BatchSession_{batch_counter}"
            batch_path = os.path.join(base_path, batch_session)
            intrinsics_calibration_path, extrinsics_calibration_path = create_folder_structure(batch_path)
            paste_config_file(batch_path)
            move_videos(source_folder, extrinsics_calibration_path, trial_date_time, trial_type, f"calib_ext_{batch_counter}")
            add_intrinsics_videos(intrinsics_calibration_path, intrinsics_videos_path)
            batch_counter += 1
            logging.info(f"Calibration videos added to {get_last_two_components(batch_path)} ; {index + 1}/{total_files} ({progress:.2f}%)")
        else:
            # Create the folder structure for a trial
            trial_counter = trial_counters.get(athlete_ID, 0) + 1
            trial_counters[athlete_ID] = trial_counter
            trial_name = f"Trial_{athlete_ID}_{trial_counter}"
            trial_path = create_folder_structure(batch_path, trial_name)
            paste_config_file(trial_path)
            move_videos(source_folder, trial_path, trial_date_time, trial_type, trial_name)
            logging.info(f"{trial_name}  videos added to {get_last_two_components(batch_path)} ; {index + 1}/{total_files} ({progress:.2f}%)")