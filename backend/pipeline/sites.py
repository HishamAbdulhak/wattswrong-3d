"""Per-site facts. Channel maps follow the NILMTK REFIT metadata (a transcription of the
REFIT ReadMe) and are checked against labelled events in reports/spike_<site>.md."""

# Houses 10 and 18 are not in the Zenodo record; they come from Strathclyde's original deposit.
ZENODO = "https://doi.org/10.5281/zenodo.5063428"
STRATHCLYDE = "https://doi.org/10.15129/9ab14b0e-19ac-4279-938f-27f643078cec"

SITES = {
    "house1": {
        "number": 1,
        "source_url": ZENODO,
        "label": "REFIT House 1 (UK)",
        "raw": {"Aggregate": "aggregate", "Appliance1": "fridge", "Appliance2": "freezer_1",
                "Appliance3": "freezer_2", "Appliance4": "washer_dryer", "Appliance5": "washing_machine",
                "Appliance6": "dishwasher", "Appliance7": "computer", "Appliance8": "television",
                "Appliance9": "electric_heater"},
        "labels": {"Fridge": "fridge", "Freezer_1": "freezer_1", "Freezer_2": "freezer_2",
                   "WashingMachine": "washing_machine", "ElectricHeater": "electric_heater"},
    },
    "house3": {
        "number": 3,
        "source_url": ZENODO,
        "label": "REFIT House 3 (UK)",
        "raw": {"Aggregate": "aggregate", "Appliance1": "toaster", "Appliance2": "fridge_freezer",
                "Appliance3": "freezer", "Appliance4": "tumble_dryer", "Appliance5": "dishwasher",
                "Appliance6": "washing_machine", "Appliance7": "television", "Appliance8": "microwave",
                "Appliance9": "kettle"},
        "labels": {"Fridge-Freezer": "fridge_freezer", "Freezer": "freezer", "Dishwasher": "dishwasher",
                   "TumbleDryer": "tumble_dryer"},
    },
    # Houses 10 and 18 are scored blind (docs/adr/0014). Channels from the REFIT ReadMe; the label
    # "Mix" is Appliance9, the Kenwood kMix (issue #4), and "Fridge_garag" is the label file's spelling.
    "house10": {
        "number": 10,
        "source_url": STRATHCLYDE,
        "label": "REFIT House 10 (UK)",
        "raw": {"Aggregate": "aggregate", "Appliance1": "magimix", "Appliance2": "toaster",
                "Appliance3": "chest_freezer", "Appliance4": "fridge_freezer", "Appliance5": "washing_machine",
                "Appliance6": "dishwasher", "Appliance7": "television", "Appliance8": "microwave",
                "Appliance9": "kmix"},
        "labels": {"ChestFreezer": "chest_freezer", "Fridge-Freezer": "fridge_freezer", "Dishwasher": "dishwasher",
                   "Mix": "kmix"},
    },
    "house18": {
        "number": 18,
        "source_url": STRATHCLYDE,
        "label": "REFIT House 18 (UK)",
        "raw": {"Aggregate": "aggregate", "Appliance1": "garage_fridge", "Appliance2": "garage_freezer",
                "Appliance3": "fridge_freezer", "Appliance4": "washer_dryer", "Appliance5": "washing_machine",
                "Appliance6": "dishwasher", "Appliance7": "computer", "Appliance8": "television",
                "Appliance9": "microwave"},
        "labels": {"Freezer_garage": "garage_freezer", "Fridge_garag": "garage_fridge",
                   "Fridge-Freezer": "fridge_freezer"},
    },
}

# Forecast (and report error for) the whole-house meter plus every labelled appliance.
# Detect findings on all of those except cycle appliances, where the day-ahead model predicts
# ~0 every hour so each normal cycle would look like excess (docs/adr/0012). Their labelled
# events still count through whole-house findings.
NO_DETECT = {"washing_machine", "dishwasher", "tumble_dryer"}
for s in SITES.values():
    s["model"] = ["aggregate", *dict.fromkeys(s["labels"].values())]
    s["detect"] = [c for c in s["model"] if c not in NO_DETECT]

NICE = {"fridge": "Fridge", "freezer_1": "Freezer 1", "freezer_2": "Freezer 2", "freezer": "Freezer",
        "fridge_freezer": "Fridge-freezer", "washing_machine": "Washing machine", "electric_heater": "Electric heater",
        "dishwasher": "Dishwasher", "tumble_dryer": "Tumble dryer", "chest_freezer": "Chest freezer",
        "kmix": "Kenwood kMix", "garage_freezer": "Garage freezer", "garage_fridge": "Garage fridge"}
COLD = {"fridge", "freezer_1", "freezer_2", "freezer", "fridge_freezer", "chest_freezer", "garage_freezer", "garage_fridge"}
