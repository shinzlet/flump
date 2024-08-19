# flump applies fillters faster

(video)

In image editing software like GIMP, you load an image, and then apply a filter. This is good for image editing, but annoying
if you're making a slide deck and want to stylize ~20 images in the same way - every time decide to add an image, you have
to load it into your image editor, then apply that filter (~5 mouse clicks), then export it somehow, then load it into your slide.

Flump turns this approach inside out - you load and configure a filter, and then push images through it. Select the right filter, then
just paste your target image in. As soon as you paste the image, Flump applies the loaded filter and copies the result to your
clipboard. For each image you want to process, just ctrl-v into flump, then ctrl-v into your slide deck.

Flump comes with small set of common image filters built in, but also supports user defined filters written using python
and common image manipulation libraries.

## Example Use Cases
- Apply the same color tint to a set of images to make your marketing materials more coherent
- Invert the luminance of an image so that a dark graphic doesn't stand out on a white slide
- Key out the greenscreen from input photos to get transparent backgrounds

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
