from io import BytesIO
import mss
from PIL import Image


class ScreenGrabber:
    """Grabs the primary screen and compresses it into a lightweight JPEG thumbnail."""

    def __init__(self) -> None:
        self.sct = mss.mss()

    def grab_thumbnail(self, width: int = 320, quality: int = 50) -> bytes:
        """
        Takes a screenshot of the primary monitor, downscales it to the target width,
        compresses it as JPEG, and returns the raw binary bytes.
        """
        # Monitor 1 represents the primary monitor (Monitor 0 is the composite virtual screen)
        monitor = self.sct.monitors[1]
        screenshot = self.sct.grab(monitor)
        
        # Convert raw BGRA bytes to PIL Image (RGB)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        
        # Calculate target height keeping aspect ratio
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio)
        
        # Downscale to low resolution to conserve bandwidth and CPU
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Compress as JPEG
        output = BytesIO()
        img_resized.save(output, format="JPEG", quality=quality)
        return output.getvalue()