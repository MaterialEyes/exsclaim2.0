import datasets


__all__ = ["classification_labels", "caption_features", "image_features"]


classification_labels = datasets.ClassLabel(
	names=[
			"Microscopy",
			"Diffraction",
			"Graph",
			"Basic Photo",
			"Illustration",
			"Unclear",
			"Parent",
			"Subfigure",
	   ]
)


caption_features = datasets.Features({
	"Journal": datasets.Value("string"),
	"ID": datasets.Value("string"), # article's ID + _fig{number},
	"Url": datasets.Value("string"),
	"Caption": datasets.Value("string"),
	"Subcaptions": [{
		"Label": datasets.Value("string"),
		"Text": datasets.Value("string"),
	}],
	"Created At": datasets.Value("timestamp[us, tz=UTC]"),
})


geometry = {
	"x0": datasets.Value("int16"),
	"y0": datasets.Value("int16"),
	"x1": datasets.Value("int16"),
	"y1": datasets.Value("int16")
}


image_features = datasets.Features({
	"Journal": datasets.Value("string"),
	"ID": datasets.Value("string"), # article's ID + _fig{number},
	"Url": datasets.Value("string"),
	"Image": datasets.Image(),
	"Info": {
		"Master Image": [{
			"classification": classification_labels,
			"geometry": geometry
		}],
		"Subfigure Label": [{
			"text": datasets.Value("string"),
			"geometry": geometry
		}],
		"Scale Bar Label": [{
			"text": datasets.Value("string"),
			"geometry": geometry
		}],
		"Scale Bar Line": [{
			"geometry": geometry
		}],
	},
	"Created At": datasets.Value("timestamp[us, tz=UTC]"),
})
