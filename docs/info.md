# TOPHAT: Tapeout Prediction with Hardware Acceleration for Trees

TOPHAT is a hardware decision-tree inference engine for a fixed depth-3 tree (7 internal nodes, 8 leaves) with 8 input features.

## Usage

### Background

A decision tree is a supervised learning model that predicts an output by applying a sequence of simple feature-based tests (for example, `feature_i < threshold`). Training determines which tests to use and where to place them so the model separates examples effectively.

At inference time, prediction is a traversal from the root to a leaf based on comparison results. In hardware the model is represented as fixed node parameters plus deterministic control flow.

For a familiar example of the sort of problem for which a decision tree can be applied, see Kaggle's [Titanic - Machine Learning from Disaster](https://www.kaggle.com/competitions/titanic).

### Model Representation

Lorem ipsum dolor.

### Feature Representation

Lorem ipsum dolor.

### Control Protocol

#### Loading a Model

Lorem ipsum dolor.

#### Prediction

Lorem ipsum dolor.

## How It Works

### Block Diagram

Lorem ipsum dolor.

### Module Descriptions

Lorem ipsum dolor.

## How to Test

Lorem ipsum dolor.

## Acknowledgments

Thanks to [BLAKE2s Hashing Accelerator: A Solo Tapeout Journey](https://essenceia.github.io/projects/blake2s_hashing_accelerator_a_solo_tapeout_journey/) for the inspiration.
