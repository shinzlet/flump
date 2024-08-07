# flump
A tool to invert the luminance of images in a very quick and simple way. Drag or paste an image into the `flump`
window - it will immediately be inverted and copied to your clipboard. You can also save to a random filename in
your downloads folder by pressing the "save to downloads" button.

## Installation Note:
`flump` requires `AppKit` for copying images to the macos clipboard. You might have to install `gobject-introspection`
to make this work:

```bash
# Install Rye (The dependency manager for this project)
# See `rye.astral.sh/guide/installation` if you're curious
curl -sSf https://rye.astral.sh/get | bash

# Install gobject-introspection
brew install gobject-introspection

# Clone the repo:
git clone https://github.com/shinzlet/flump.git

# Run flump:
cd flump
rye sync
rye run flump
```
