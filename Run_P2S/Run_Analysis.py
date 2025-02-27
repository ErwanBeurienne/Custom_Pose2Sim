import sys
import os

# Ajouter le chemin absolu de Package_P2S
print(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Package_P2S')))

from Pose2Sim import Pose2Sim

Pose2Sim.calibration()
