import platform
from PIL import Image
import io

system = platform.system()
if system == "Windows":
    from win32 import win32clipboard as clip
    def copy_image(image: Image.Image):
        clip.OpenClipboard()
        clip.EmptyClipboard()

        output = io.BytesIO()
        png_format = clip.RegisterClipboardFormat("PNG")
        image.save(output, format="PNG")
        clip.SetClipboardData(png_format, output.getvalue())
        output.close()

        output = io.BytesIO()
        image.save(output, format="DIB")
        clip.SetClipboardData(clip.CF_DIB, output.getvalue())

        clip.CloseClipboard()

elif system == "Darwin":
    import AppKit
    def copy_image(image: Image.Image):
        output = io.BytesIO()
        image.save(output, format="PNG")
        ns_image = AppKit.NSImage.alloc().initWithData_(
            AppKit.NSData.dataWithBytes_length_(output.getvalue(), len(output.getvalue()))
        )

        pb = AppKit.NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setData_forType_(ns_image.TIFFRepresentation(), AppKit.NSTIFFPboardType)
        output.close()

elif system == "Linux":
    raise RuntimeError("Linux is not a currently supported platform!")