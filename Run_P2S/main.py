import Pre_Processing
import os

# Exemple d'utilisation
source_folder = "../../../03_Experimental_Humain/Montreal/Session_18.02.25"
destination_folder = source_folder
excel_file_path = os.path.join(source_folder, "experimental_test_log.xlsx")
intrinsics_calibration_path = os.path.join(source_folder,"intrinsics_calibration")

Pre_Processing.organize_videos(excel_file_path, source_folder, destination_folder, intrinsics_calibration_path)
