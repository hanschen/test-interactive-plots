"""Display sliders and thermometers for a model."""

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from ipywidgets import AppLayout, HBox, VBox, widgets

from localization import localize


def run(model, parameters, title=None, colors=None, **kwargs):
    """Display control widgets and model output.

    ``model`` is a callable for the model.

    ``parameters`` is a dict with parameter names as keys and initial values as values.

    Accepts optional title for the figure, list of colors for the thermometers, and
    kwargs passed to the Thermometer class.
    """

    temperatures = model(**parameters)

    num_thermometers = len(temperatures)
    if colors is None:
        colors = ["r", "b"] * num_thermometers

    with plt.ioff():
        fig, axes = plt.subplots(1, num_thermometers)
        fig.canvas.header_visible = False
        fig.canvas.toolbar_visible = False
        fig.canvas.footer_visible = False
        fig.canvas.resizable = False

    if title is not None:
        fig.suptitle(localize(title))

    # Create control widgets
    widgets = []
    sliders = []

    for param, value in parameters.items():
        description_label = _create_decription_label(param)
        slider = _create_slider(param, value)
        unit_label = _create_unit_label(param)
        sliders.append(slider)
        widgets.append(HBox([description_label, slider, unit_label]))

    # Workaround for when there is only one thermometer
    if num_thermometers == 1:
        axes = [axes]

    # Create the initial thermometers.
    thermometers = []
    for i, (description, temperature) in enumerate(temperatures.items()):
        kwargs_current = kwargs.copy()
        kwargs_current["facecolor"] = colors[i]
        thermometer = Thermometer(**kwargs_current)
        thermometer.draw(temperature, ax=axes[i], description=description)
        thermometers.append(thermometer)

    # Update them when a slider changes
    def update(change):
        temperatures = model(*[slider.value for slider in sliders])
        for i, (description, temperature) in enumerate(temperatures.items()):
            kwargs_current = kwargs.copy()
            kwargs_current["facecolor"] = colors[i]
            # Re-draw the thermometer instead of creating a new one.
            thermometers[i].draw(temperature, ax=axes[i], description=description)

        fig.canvas.draw()
        fig.canvas.flush_events()

    [slider.observe(update, names="value") for slider in sliders]

    return AppLayout(
        header=VBox(widgets),
        center=fig.canvas,
        pane_heights=[1, 6, 0],
    )


def _create_slider(variable, value):
    """Return a slider widget for ``variable``.

    Parameters
    ----------
    variable : {"temperature", "solar", "albedo", "emissivity"}
        The variable to create the slider for.

    """
    layout = widgets.Layout(width="60%", height="auto")

    if variable == "temperature":
        minval = -273.0
        maxval = 100.0
        step = 1.0
        readout_format = ".0f"
    elif variable == "solar_intensity_percent":
        minval = 50.0
        maxval = 150.0
        step = 1.0
        readout_format = ".0f"
    elif variable == "planet_albedo":
        minval = 0.0
        maxval = 1.0
        step = 0.01
        readout_format = ".2f"
    elif variable == "infrared_emissivity":
        minval = 0.1
        maxval = 1.0
        step = 0.005
        readout_format = ".3f"
    elif variable == "optical_absorptivity":
        minval = 0.0
        maxval = 0.5
        step = 0.005
        readout_format = ".3f"
    else:
        raise ValueError(f"invalid variable: {variable}")

    return widgets.FloatSlider(
        value=value,
        min=minval,
        max=maxval,
        step=step,
        readout_format=readout_format,
        layout=layout,
    )


def _create_decription_label(variable):
    descriptions = {
        "temperature": "Temperature",
        "solar_intensity_percent": "Solar intensity",
        "planet_albedo": "Planet albedo",
        "infrared_emissivity": "Infrared emissivity",
        "optical_absorptivity": "Optical absorptivity",
    }
    layout = widgets.Layout(
        width="20%", height="auto", display="flex", justify_content="flex-end"
    )
    description = localize(descriptions[variable])
    return widgets.Label(description, layout=layout)


def _create_unit_label(variable):
    units = {
        "temperature": "°C",
        "solar_intensity_percent": "% of present value",
        "planet_albedo": "(fraction)",
        "infrared_emissivity": "(fraction)",
        "optical_absorptivity": "(fraction)",
    }
    layout = widgets.Layout(width="20%", height="auto")
    unit = localize(units[variable])
    return widgets.Label(unit, layout=layout)


class Thermometer:
    def __init__(
        self,
        min=-273.15,
        max=100.0,
        units=" °C",
        barwidth=40,
        bulbwidth=None,
        linewidth=3.0,
        facecolor="r",
        edgecolor="k",
        padding_x=5.0,
        padding_y=8.0,
    ):
        """Initialize the Thermometer.

        The thermometer consists of a "bar" and a "bulb" at the bottom.

        Note that the unit for all sizes (``barwidth``, ``linewidth``, etc.) are in data
        units, so the same units as the temperature.

        Parameters
        ----------
        min : float
            Min temperature of the thermometer. Default: -273.15.
        max : float
            Max temperature of the thermometer. Default: 100.0.
        units : str
            Units for the temperature. Only affects displayed text and tick labels.
        barwidth : float, optional
            Width of the bar of the thermometer. Default: 40.0.
        bulbwidth : float, optional
            Width (and height) of the bulb. Default: Twice of ``barwidth``.
        linewidth : float, optional
            Width of the line outlining the thermometer. Default: 3.0.
        facecolor : color or None
            Color of temperature fill. Default: "r".
        edgecolor : color or None
            Color of thermometer outline. Default: "k".
        padding_x : float, optional
            Padding around thermometer in the x-direction. Default: 5.0.
        padding_y : float, optional
            Padding around thermometer in the y-direction. Default: 8.0.

        """
        self.min = min
        self.max = max
        self.units = units
        self.barwidth = barwidth
        if bulbwidth is None:
            bulbwidth = 2 * barwidth
        self.bulbwidth = bulbwidth
        self.linewidth = linewidth
        self.facecolor = facecolor
        self.edgecolor = edgecolor
        self.padding_x = padding_x
        self.padding_y = padding_y

        self.ax = None

        self._temp_bulb = None
        self._temp_bar = None
        self._temp_text = None

    @property
    def bar_height(self):
        return self.max - self.origin_y

    @property
    def origin_y(self):
        """y-coordinate for the bottom of the bar and the middle of the bulb."""
        return self.min + self.bulbwidth / 2

    @property
    def xmax(self):
        return self.barwidth + self.padding_x

    @property
    def xmin(self):
        return -self.barwidth - self.padding_x

    @property
    def ymax(self):
        return self.max + self.padding_y

    @property
    def ymin(self):
        return self.min - self.padding_y

    def draw(
        self, temperature, ax=None, display_value=True, title=None, description=None
    ):
        """Draw a thermometer with a temperature reading.

        Parameters
        ----------
        temperature : float
            Temperature to show.
        ax : None or matplotlib.axes.Axes, optional
            Axes object to draw to. If not given, the method will create a new Axes
            object in a new figure.
        display_value : bool, optional
            If True (default), display the current value to the left.
        title : None or str, optional
            String to use as figure title.
        description : None or str, optional
            Description to display at the bottom.

        """
        # Draw outline if necessary
        if self.ax is None:
            self.draw_outline(ax=ax)

        if ax is None:
            ax = self.ax

        self._create_bar(ax, temperature)
        if title:
            ax.get_figure().suptitle(title)

        if description:
            ax.set_xlabel(localize(description))

        if self._temp_text is not None:
            self._temp_text.remove()

        if display_value:
            self._temp_text = ax.text(
                self.xmax,
                temperature,
                f"{temperature:.1f}{self.units}",
                horizontalalignment="left",
                verticalalignment="center",
                color=self.facecolor,
            )

    def draw_outline(self, ax=None):
        """Draw outline of the thermometer.

        Parameters
        ----------
        ax : None or matplotlib.axes.Axes, optional
            Axes object to draw to. If not given, the method will create a new Axes
            object in a new figure.

        Returns
        -------
        matplotlib.axes.Axes:
            Axes object containing the thermometer.

        """
        if ax is None:
            _, ax = plt.subplots()

        # NOTE: Don't know how to draw the common outline of two patches, so here we
        # cheat by first drawing an "outer" part and then an "inner" part filled with
        # white

        outer_bulb = patches.Circle(
            (0, self.origin_y),
            radius=self.bulbwidth / 2,
            color=self.edgecolor,
            linewidth=0,
        )
        outer_bar = patches.Rectangle(
            (-self.barwidth / 2, self.origin_y),
            width=self.barwidth,
            height=self.bar_height,
            color=self.edgecolor,
            linewidth=0,
        )
        inner_bulb = self._get_inner_bulb(color="w")
        inner_bar = self._get_inner_bar(color="w")

        ax.add_patch(outer_bulb)
        ax.add_patch(outer_bar)
        ax.add_patch(inner_bulb)
        ax.add_patch(inner_bar)

        ax.set_aspect("equal")
        ax.set_xlim(self.xmin, self.xmax)
        ax.set_ylim(self.ymin, self.ymax)
        ax.set_xticks([])
        ax.spines[["right", "top", "bottom"]].set_visible(False)

        yticks = [tick for tick in ax.get_yticks() if self.min <= tick <= self.max]
        yticklabels = [f"{tick:.0f}{self.units}" for tick in yticks]
        ax.set_yticks(yticks, yticklabels)

        self.ax = ax

        return ax

    def _create_bar(self, ax, temperature):
        # Remove old elements
        if self._temp_bar is not None:
            self._temp_bar.remove()
        if self._temp_bulb is not None:
            self._temp_bulb.remove()

        width = self.xmax - self.xmin
        height = temperature - self.min

        # Need two temperature patches, one for the bulb part and one for the bar
        self._temp_bulb = patches.Rectangle(
            (self.xmin, self.min), width=width, height=height, color=self.facecolor
        )
        self._temp_bar = patches.Rectangle(
            (self.xmin, self.min), width=width, height=height, color=self.facecolor
        )

        ax.add_patch(self._temp_bulb)
        ax.add_patch(self._temp_bar)

        inner_bulb = self._get_inner_bulb()
        inner_bar = self._get_inner_bar()

        # Need to add these clip patches to ax to get the coordinates right
        ax.add_patch(inner_bulb)
        ax.add_patch(inner_bar)

        self._temp_bulb.set_clip_path(inner_bulb)
        self._temp_bar.set_clip_path(inner_bar)

    def _get_inner_bulb(self, color="none"):
        inner_bulb = patches.Circle(
            (0, self.origin_y),
            radius=self.bulbwidth / 2 - self.linewidth,
            color=color,
            linewidth=0,
        )
        return inner_bulb

    def _get_inner_bar(self, color="none"):
        inner_bar = patches.Rectangle(
            (-self.barwidth / 2 + self.linewidth, self.origin_y),
            width=self.barwidth - 2 * self.linewidth,
            height=self.bar_height - self.linewidth,
            color=color,
            linewidth=0,
        )
        return inner_bar
