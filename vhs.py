#!/usr/bin/env python

#   The GIMP VHS plugin - PAL VHS effect plugin for The GIMP.
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
VHS_BLACK = (0, 0, 0)

# TODO make the head change luminance fade by around 60%
# TODO add comet tails

def vhs(img, layer, add_border, add_messy, add_glitch, glitch_y,
        down_interpol, up_interpol):

    gimp.context_push()
    img.undo_group_start()

    # Scale image to PAL size (720 x 576)
    scale_to_pal(img, down_interpol, up_interpol)

    # Add VHS border if required
    if add_border:
        layer = add_vhs_border(img, layer)

    # Add messy head change if required
    if add_messy:
        layer = add_messy_head_change(img, layer)

    # Add glitch if required
    if add_glitch:
        layer = add_vhs_glitch(img, layer, glitch_y)

    # Work out image scaling
    width = layer.width
    height = layer.height

    chrominance_width = width * 0.1625
    chrominance_height = height
    luminance_width = width * 0.4625
    luminance_height = height

    # Luminance layer
    luminance_layer = layer

    # Create a chrominance layer
    add_alpha = True
    chrominance_layer = pdb.gimp_layer_copy(layer, add_alpha)
    pdb.gimp_image_add_layer(img, chrominance_layer, -1)
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
    pdb.gimp_image_merge_down(img, chrominance_layer, CLIP_TO_IMAGE)

    img.undo_group_end()
    gimp.context_pop()

def is_pal_sized(image):
    return image.width == PAL_WIDTH and image.height == PAL_HEIGHT

def scale(layer, new_width, new_height, interpolation):
    local_origin = False    
    pdb.gimp_layer_scale_full(layer, new_width, new_height, local_origin,
                              interpolation)

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

def add_vhs_border(image, layer):
    """Adds a black border to the area of layer that would not contain VHS
    picture information on a real VHS screen grab.

    The position parameter is important, so the black border is added to the
    correct layer.

    Returns the new layer created as a result of the border layer being merged
    with layer."""
    
    # Create a new layer above layer
    opacity = 100
    position = pdb.gimp_image_get_layer_position(image, layer)
    new_layer = pdb.gimp_layer_new(image, PAL_WIDTH, PAL_HEIGHT, RGBA_IMAGE, 
                                   "VHS border", opacity, NORMAL_MODE)
    pdb.gimp_image_add_layer(image, new_layer, position)
    gimp.set_foreground(VHS_BLACK)
    pdb.gimp_edit_fill(new_layer, FOREGROUND_FILL)

    # Cut out a VHS sized hole from new layer
    VHS_WIDTH = 700
    VHS_HEIGHT = 524
    VHS_X = 10
    VHS_Y = 26
    feather = True
    feather_radius = 2.0
    pdb.gimp_rect_select(image, VHS_X, VHS_Y, VHS_WIDTH, VHS_HEIGHT, 
                         CHANNEL_OP_REPLACE, feather, feather_radius)
    pdb.gimp_edit_cut(new_layer)
    pdb.gimp_selection_none(image) 

    # Merge layer with current image
    return pdb.gimp_image_merge_down(image, new_layer, CLIP_TO_IMAGE)

def shift_lines(image, layer, shift_values, start_y):
    """Shift a sucession of screen lines by the amounts in the tuple
    shift_values, starting from start_y and working downwards.

    Returns reference to the new layer that results from the shift."""

    # Create a new duplicate layer above the existing one
    add_alpha = False
    position = pdb.gimp_image_get_layer_position(image, layer)
    gimp.set_background(VHS_BLACK)
    new_layer = pdb.gimp_layer_copy(layer, add_alpha)
    pdb.gimp_image_add_layer(image, new_layer, position)

    # Make original layer black
    feather = False
    feather_radius = 0.0
    pdb.gimp_rect_select(image, 0, 0, PAL_WIDTH, PAL_HEIGHT, 
                         CHANNEL_OP_REPLACE, feather, feather_radius)
    gimp.set_foreground(VHS_BLACK)
    pdb.gimp_edit_fill(layer, FOREGROUND_FILL)

    # Shift screen lines on the new layer
    dy = 0
    start_x = 0
    line_width = PAL_WIDTH
    line_height = 1

    for dx in shift_values:
        pdb.gimp_rect_select(image, start_x, start_y, line_width, line_height, 
                             CHANNEL_OP_REPLACE, feather, feather_radius)
        float_layer = pdb.gimp_selection_float(new_layer, dx, dy)
        pdb.gimp_floating_sel_anchor(float_layer)
        pdb.gimp_selection_none(image)
        start_y += 1

    # Merge the new layer with the original layer
    return pdb.gimp_image_merge_down(image, new_layer, CLIP_TO_IMAGE)

def add_vhs_glitch(image, layer, start_y = 146):
    """Simulates a typical VHS glitch to layer at the specified y value."""

    shift_values = (9, 9, 6, 4, 2, 1)
    return shift_lines(image, layer, shift_values, start_y)

def add_messy_head_change(image, layer):
    """Simulates a messy VHS tape head change at the bottom of layer."""

    shift_values = (21, 23, 5, 5, 6)
    start_y = 545
    return shift_lines(image, layer, shift_values, start_y)


register(
    "python-fu-vhs",
    N_("Makes image look like it came from a PAL VHS tape."),
    "Makes image look like it came from a PAL VHS tape.",
    "Dave Jeffery",
    "Dave Jeffery",
    "2009",
    N_("V_HS..."),
    "RGB*, GRAY*",
    [
        (PF_IMAGE, "image", _("Input image"), None),
        (PF_DRAWABLE, "drawable", _("Input drawable"), None),
        (PF_TOGGLE, "add_border", _("Add VHS border?"), True),
        (PF_TOGGLE, "add_messy", _("Add messy head change?"), True),
        (PF_TOGGLE, "add_glitch", _("Add glitch?"), True),
	(PF_SLIDER, "glitch_y", _("Glitch y-position (pixels)"), 146, (0, 545, 1)),
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
    vhs,
    menu="<Image>/Filters/Artistic",
    domain=("gimp20-python", gimp.locale_directory)
    )

main()
