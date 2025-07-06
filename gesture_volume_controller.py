import cv2
import numpy as np
import mediapipe as mp
import math
import platform
import subprocess
import os
import sys

class GestureVolumeController:
    def __init__(self):
        # Initialize MediaPipe hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Volume control parameters
        self.min_vol = 0
        self.max_vol = 100
        self.vol = 0
        self.vol_per = 0
        
        # Gesture parameters
        self.min_hand_distance = 30
        self.max_hand_distance = 200
        
        # Smoothing parameters
        self.volume_history = []
        self.vol_per_history = []
        self.history_size = 5
        
        # OS detection for volume control
        self.os_type = platform.system()
        
        # Initialize volume tracking
        self.current_vol_smooth = 0
        self.current_vol_per_smooth = 0
        
    def set_volume(self, volume):
        """Set system volume based on OS"""
        try:
            if self.os_type == "Windows":
                # Try pycaw first (more reliable)
                try:
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    from comtypes import CLSCTX_ALL
                    from ctypes import cast, POINTER
                    
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                    volume_interface.SetMasterScalarVolume(volume / 100.0, None)
                except ImportError:
                    # Fallback to nircmd
                    os.system(f"nircmd setsysvolume {int(volume * 655.35)}")
            elif self.os_type == "Darwin":  # macOS
                os.system(f"osascript -e 'set volume output volume {volume}'")
            elif self.os_type == "Linux":
                # Linux using amixer
                os.system(f"amixer -D pulse sset Master {volume}%")
        except Exception as e:
            print(f"Error setting volume: {e}")
    
    def get_distance(self, point1, point2):
        """Calculate distance between two points"""
        return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)
    
    def smooth_volume(self, current_vol, history_list):
        """Apply smoothing to volume changes"""
        history_list.append(current_vol)
        if len(history_list) > self.history_size:
            history_list.pop(0)
        return int(sum(history_list) / len(history_list))
    
    def draw_volume_bar(self, img, vol_per):
        """Draw volume bar on the image"""
        # Volume bar background
        cv2.rectangle(img, (50, 150), (85, 400), (255, 0, 0), 3)
        
        # Volume bar fill
        bar_height = int(vol_per * 2.5)
        cv2.rectangle(img, (50, int(400 - bar_height)), (85, 400), (255, 0, 0), cv2.FILLED)
        
        # Volume percentage text
        cv2.putText(img, f'{int(vol_per)}%', (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)
        
        # Instructions
        cv2.putText(img, 'Pinch to Control Volume', (200, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, 'Press Q to Quit', (200, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Volume level indicator
        color = (0, 255, 0) if vol_per > 0 else (0, 0, 255)
        cv2.putText(img, f'Volume: {int(vol_per)}%', (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    def run(self):
        """Main execution loop"""
        cap = cv2.VideoCapture(0)
        
        # Check if camera opened successfully
        if not cap.isOpened():
            print("Error: Could not open camera")
            print("Make sure your camera is connected and not being used by another application")
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("Gesture Volume Controller Started!")
        print("Instructions:")
        print("- Show your hand to the camera")
        print("- Pinch thumb and index finger together to control volume")
        print("- Closer pinch = lower volume, farther apart = higher volume")
        print("- Press 'q' to quit")
        print("- Press 'r' to reset volume history")
        
        while True:
            success, img = cap.read()
            if not success:
                print("Failed to read from camera")
                break
            
            # Flip image horizontally for mirror effect
            img = cv2.flip(img, 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Process hand detection
            results = self.hands.process(img_rgb)
            
            hand_detected = False
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    hand_detected = True
                    
                    # Draw hand landmarks
                    self.mp_drawing.draw_landmarks(img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    # Get landmark positions
                    landmarks = []
                    for lm in hand_landmarks.landmark:
                        h, w, c = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        landmarks.append([cx, cy])
                    
                    # Get thumb tip (4) and index finger tip (8) positions
                    if len(landmarks) >= 9:
                        thumb_tip = landmarks[4]
                        index_tip = landmarks[8]
                        
                        # Draw circles on fingertips
                        cv2.circle(img, tuple(thumb_tip), 15, (255, 0, 255), cv2.FILLED)
                        cv2.circle(img, tuple(index_tip), 15, (255, 0, 255), cv2.FILLED)
                        
                        # Draw line between fingertips
                        cv2.line(img, tuple(thumb_tip), tuple(index_tip), (255, 0, 255), 3)
                        
                        # Calculate distance between fingertips
                        distance = self.get_distance(thumb_tip, index_tip)
                        
                        # Clamp distance to valid range
                        distance = max(self.min_hand_distance, min(distance, self.max_hand_distance))
                        
                        # Map distance to volume (inverted for intuitive control)
                        vol = np.interp(distance, [self.min_hand_distance, self.max_hand_distance], [self.max_vol, self.min_vol])
                        vol_per = np.interp(distance, [self.min_hand_distance, self.max_hand_distance], [100, 0])
                        
                        # Apply smoothing
                        self.current_vol_smooth = self.smooth_volume(vol, self.volume_history)
                        self.current_vol_per_smooth = self.smooth_volume(vol_per, self.vol_per_history)
                        
                        # Set system volume
                        self.set_volume(self.current_vol_smooth)
                        
                        # Visual feedback for pinch detection
                        if distance < 50:
                            cv2.circle(img, ((thumb_tip[0] + index_tip[0]) // 2, (thumb_tip[1] + index_tip[1]) // 2), 15, (0, 255, 0), cv2.FILLED)
                        
                        # Display distance
                        cv2.putText(img, f'Distance: {int(distance)}', (200, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Show "No Hand Detected" message when no hand is visible
            if not hand_detected:
                cv2.putText(img, 'No Hand Detected', (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(img, 'Show your hand to camera', (200, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Draw volume bar
            self.draw_volume_bar(img, self.current_vol_per_smooth)
            
            # Display the image
            cv2.imshow('Gesture Volume Controller', img)
            
            # Check for quit or reset
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # Reset volume history for recalibration
                self.volume_history.clear()
                self.vol_per_history.clear()
                print("Volume history reset!")
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("Gesture Volume Controller stopped!")

# Additional utility functions for different volume control methods
def install_requirements():
    """Install required packages"""
    packages = ['opencv-python', 'mediapipe', 'numpy']
    
    # Add pycaw for Windows users
    if platform.system() == "Windows":
        packages.append('pycaw')
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")

def setup_windows_volume():
    """Setup instructions for Windows volume control"""
    print("\nFor Windows users:")
    print("Option 1 (Recommended): Install pycaw library")
    print("  pip install pycaw")
    print("\nOption 2: Download nircmd.exe")
    print("  1. Download from https://www.nirsoft.net/utils/nircmd.html")
    print("  2. Place nircmd.exe in your system PATH or same directory as script")

def check_camera():
    """Check if camera is available"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Camera not found or already in use")
        print("Solutions:")
        print("1. Make sure your camera is connected")
        print("2. Close other applications using the camera")
        print("3. Try running as administrator")
        return False
    else:
        cap.release()
        print("✓ Camera available")
        return True

if __name__ == "__main__":
    # Check if running directly
    print("Gesture Volume Controller")
    print("=" * 50)
    
    # Install requirements if needed
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError:
        print("Installing required packages...")
        install_requirements()
        print("Please restart the script after installation.")
        sys.exit(1)
    
    # Check camera availability
    if not check_camera():
        input("Press Enter to continue anyway...")
    
    # Setup instructions
    if platform.system() == "Windows":
        setup_windows_volume()
    
    # Run the controller
    try:
        controller = GestureVolumeController()
        controller.run()
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure all dependencies are installed and camera is available")
