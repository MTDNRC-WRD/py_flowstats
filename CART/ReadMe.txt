ReadMe

---

# Montana Streamflow Classification (CART Analysis)

## Project Overview

This project uses **Classification and Regression Trees (CART)** to help understand the physical and climatic drivers behind streamflow regimes in Montana. The main classification and prediction was done with a Random Forest algorithm, but the CART produces a decision splits output that helps understand where classes differ in terms of basin attributes. By analyzing various watershed attributes, we have identified key "hard thresholds"—such as elevation, soil texture, and precipitation seasonality—that define our five primary stream categories.

---

## 🛠 Setup & Installation

To reproduce this analysis, you must use the custom Conda environment provided in the `environment.yml` file. This ensures all library versions (scikit-learn, pandas, etc.) match the original study.

### 1. Create the Environment

Open your **Anaconda Prompt**, navigate to this project folder, and run:

```bash
conda env create -f environment.yml

```

### 2. Activate the Environment

```bash
conda activate sklearn-env

```

### 3. Dependency Note: Graphviz

This script generates PDF visualizations of the decision trees.

* You must have **Graphviz** installed on your system.
* In the `CART.py` script, ensure the `os.environ["PATH"]` line points to your local Graphviz `bin` folder.

---

## 🌲 Key Classification Thresholds

The classification is built on two complementary models: a **Full Model** (driven by elevation) and a **Thinned Model** (revealing secondary process drivers).

### Primary Drivers

Based on our CART analysis, the following variables are the most significant "gatekeepers" for Montana hydrology:

* 
**Elevation ():** The primary split occurs at ** meters** (~6,200 ft), separating high-alpine snowmelt regimes from foothills and plains.


* 
**Precipitation Seasonality ():** A ratio of **** serves as a critical divider between rain-dominated lowland systems and snow-dominated mountain systems.


* 
**Soil Texture ():** High clay content (****) is the primary driver for "buffered" or stable summer flows, as it increases subsurface water retention.


* 
**Aridity Index:** A threshold of **** identifies specific high-storage/groundwater-influenced regimes in the Northwest.



---

## 📊 Summary of Stream Categories

| Category | Tentative Name | Defining Drivers |
| --- | --- | --- |
| **0** | **Alpine Snowmelt** | Elevation  m and Conifer Cover .

 |
| **1** | **Flashy Lowland** | Low winter/summer precip ratio () and minimal April snowpack ( mm).

 |
| **2** | **Transitional Foothills** | Mid-elevation with moderate April snowpack ( mm) or moderate forest cover.

 |
| **4** | **Buffered Snowmelt** | Characterized by high soil clay content () which sustains summer flows.

 |
| **5** | **High Storage** | Arid-buffered regimes ( aridity) with stable baseflow.

 |

---

## 🚀 Usage

To run the classification and generate new decision tree PDFs and confusion matrices:

1. Ensure your input CSV of watershed attributes is in the `Data` directory.
2. Run the script: `python CART.py`

---

**Would you like me to help you draft a formal "Results" paragraph for your thesis that uses this table as a reference?**