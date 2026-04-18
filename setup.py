from setuptools import setup

APP = ["src/app.py"]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns",
    "plist": {
        "CFBundleName": "Eye Strain Timer",
        "CFBundleDisplayName": "Eye Strain Timer",
        "CFBundleIdentifier": "com.tony.eye-strain-timer",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
}

setup(
    name="Eye Strain Timer",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
