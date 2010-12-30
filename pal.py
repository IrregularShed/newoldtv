#!/usr/bin/env python

#   The GIMP PAL plugin - PAL effect plugin for The GIMP.
#   Copyright (C) 2009  Dave Jeffery <david.richard.jeffery@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gimpfu import *

gettext.install("gimp20-python", gimp.locale_directory, unicode=True)

# Constants definitions
PAL_WIDTH = 720
PAL_HEIGHT = 576
PAL_BLACK = (0, 0, 0)
PAL_S = 1.0
PAL_D = 0.5

def pal(img, layer, add_border, add_interlace, pal_y_scale,
        down_interpol, up_interpol):
    """Simulates PAL encoding on an image. To do this it uses the source
    image to make two new images: a high resolution "luminance" image and a
    low resolution "chrominance" image. Then it combines these two images to
    give you the finished result.

    The method used by this plug-in is explained in more detail on my blog:
    http://kecskebak.blogspot.com/2009/09/tapeheads-revisited.html

    There are some additional features such as adding the borders to the edge
    of the image, a crude 'interlace' effect and a choice of PAL encoding
    systems.

    PAL-D averages out the colour of adjacent lines, so to simulate this I
    simply halve the vertical resolution when creating the luminance and
    chrominance images.

    The plug-in makes scales the source image 720 x 576 before it begins."""

    gimp.context_push()
    img.undo_group_start()

    # Scale image to PAL size (720 x 576)
    scale_to_pal(img, down_interpol, up_interpol)

    # Add PAL border if required
    if add_border:
        layer = add_pal_border(img, layer)

    # Work out image scaling
    width = layer.width
    height = layer.height

    chrominance_width = width / 3
    chrominance_height = height * pal_y_scale
    luminance_width = width - chrominance_width
    luminance_height = height * pal_y_scale

    # Luminance layer
    luminance_layer = layer

    # Create a chrominance layer
    chrominance_layer = layer.copy(1)
    img.add_layer(chrominance_layer)
    pdb.gimp_layer_set_mode(chrominance_layer, ADDITION_MODE)

    # Apply levels to luminance layer
    adjust_levels(luminance_layer, 76, 150, 29)

    # Apply levels to chrominance layer
    adjust_levels(chrominance_layer, 179, 105, 226)

    # Scale luminance layer
    scale(luminance_layer, luminance_width, luminance_height,
          down_interpol) 
    scale(luminance_layer, width, height, up_interpol)

    # Scale chrominance layer
    scale(chrominance_layer, chrominance_width, chrominance_height,
          down_interpol) 
    scale(chrominance_layer, width, height, up_interpol)

    # Merge chrominance and luminance layers
    layer = pdb.gimp_image_merge_down(img, chrominance_layer, CLIP_TO_IMAGE)

    # Add interlace effect if required
    if add_interlace:
        layer = add_interlace_effect(img, layer)

    img.undo_group_end()
    gimp.context_pop()

def scale(layer, new_width, new_height, interpolation):
    local_origin = False    
    pdb.gimp_layer_scale_full(layer, new_width, new_height, local_origin,
                              interpolation)

def is_pal_sized(image):
    return image.width == PAL_WIDTH and image.height == PAL_HEIGHT

def scale_to_pal(image, down_interpol, up_interpol):
    """Scales image to standard PAL size - 720 x 576 pixels.
    If the image is bigger, use the user specified downscaling method,
    otherwise use the user specified upscaling method."""

    # Check to make sure image is not 720 x 576 already
    if is_pal_sized(image):
        return

    # Choose which interpolation method to use to scale image
    if image.width > PAL_WIDTH:
        interpolation = down_interpol
    else:
        interpolation = up_interpol

    # Scale image
    pdb.gimp_image_scale_full(image, PAL_WIDTH, PAL_HEIGHT, interpolation)

def adjust_levels(layer, r, g, b):
    low_input = 0
    high_input = 255
    gamma = 1.0
    low_output = 0

    pdb.gimp_levels(layer , HISTOGRAM_RED, low_input, high_input,
                    gamma, low_output, r)
    pdb.gimp_levels(layer , HISTOGRAM_GREEN, low_input, high_input,
                    gamma, low_output, g)
    pdb.gimp_levels(layer , HISTOGRAM_BLUE, low_input, high_input,
                    gamma, low_output, b)

def add_pal_border(image, layer):
    """Adds a black border to the area of layer that would not contain PAL
    picture information on a real PAL screen grab.

    The position parameter is important, so the black border is added to the
    correct layer.

    Returns the new layer created as a result of the border layer being merged
    with layer."""
    
    # Create a new layer above layer
    opacity = 100
    position = pdb.gimp_image_get_layer_position(image, layer)
    new_layer = pdb.gimp_layer_new(image, PAL_WIDTH, PAL_HEIGHT, RGBA_IMAGE, 
                                   "PAL border", opacity, NORMAL_MODE)
    pdb.gimp_image_add_layer(image, new_layer, position)
    gimp.set_foreground(PAL_BLACK)
    pdb.gimp_edit_fill(new_layer, FOREGROUND_FILL)

    # Cut out hole from new layer
    BOR_WIDTH = 702
    BOR_HEIGHT = 576
    BOR_X = 9
    BOR_Y = 0
    feather = True
    feather_radius = 2.0
    pdb.gimp_rect_select(image, BOR_X, BOR_Y, BOR_WIDTH, BOR_HEIGHT, 
                         CHANNEL_OP_REPLACE, feather, feather_radius)
    pdb.gimp_edit_cut(new_layer)
    pdb.gimp_selection_none(image) 

    # Merge layer with current image
    return pdb.gimp_image_merge_down(image, new_layer, CLIP_TO_IMAGE)

def add_interlace_effect(image, layer):
    """Creates an interlace style effect.

    Returns the new layer that results from adding the effect."""

    # Create a new duplicate layer above the existing one
    add_alpha = True
    position = pdb.gimp_image_get_layer_position(image, layer)
    new_layer = pdb.gimp_layer_copy(layer, add_alpha)
    pdb.gimp_image_add_layer(image, new_layer, position)

    # Shift screen lines on the new layer
    dy = 0
    dx = 1
    feather = False
    feather_radius = 0.0
    line_width = new_layer.width
    line_height = 1
    start_x = 0

    for start_y in range(0, new_layer.height, 2):
        pdb.gimp_rect_select(image, start_x, start_y, line_width, line_height, 
                             CHANNEL_OP_REPLACE, feather, feather_radius)
        float_layer = pdb.gimp_selection_float(new_layer, dx, dy)
        pdb.gimp_floating_sel_anchor(float_layer)
        pdb.gimp_selection_none(image)

    # Apply Gaussian Blue to new layer
    horizontal = 1.0
    vertical = 1.0
    method = 1     # No constants available IIR = 0, RLE = 1
    pdb.plug_in_gauss(image, new_layer, horizontal, vertical, method)

    # Merge the new layer with the original layer
    return pdb.gimp_image_merge_down(image, new_layer, CLIP_TO_IMAGE)


register(
    "python-fu-pal",
    N_("Makes image look PAL encoded."),
    "Makes image look PAL encoded.",
    "Dave Jeffery",
    "Dave Jeffery",
    "2009",
    N_("_PAL..."),
    "RGB*, GRAY*",
    [
        (PF_IMAGE, "image", _("Input image"), None),
        (PF_DRAWABLE, "drawable", _("Input drawable"), None),
        (PF_TOGGLE, "add_border", _("Add PAL border?"), True),
        (PF_TOGGLE, "add_interlace", _("Add interlace effect?"), True),
        (PF_RADIO, "pal_y_scale", _("PAL version"), 1.0,
         ((_("PAL-S (Simple PAL)"), PAL_S),
          (_("PAL-D"), PAL_D))),
        (PF_RADIO, "down_interpol", _("Down-scaling interpolation method"), 2,
         ((_("None"), INTERPOLATION_NONE),
          (_("Linear"), INTERPOLATION_LINEAR),
          (_("Cubic"), INTERPOLATION_CUBIC),
          (_("Sinc Lanczos"), INTERPOLATION_LANCZOS))),
        (PF_RADIO, "up_interpol", _("Up-scaling interpolation method"), 3,
         ((_("None"), INTERPOLATION_NONE),
          (_("Linear"), INTERPOLATION_LINEAR),
          (_("Cubic"), INTERPOLATION_CUBIC),
          (_("Sinc Lanczos"), INTERPOLATION_LANCZOS)))        
    ],
    [],
    pal,
    menu="<Image>/Filters/Artistic",
    domain=("gimp20-python", gimp.locale_directory)
    )

main()
