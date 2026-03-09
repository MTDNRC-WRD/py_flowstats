import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn import tree
import os
os.environ["PATH"] += os.pathsep + 'C:/Users/CN0401/.conda/envs/sklearn-env/Library/bin/'
import graphviz

def cart_analysis(file_path, dependent_variable, independent_variables, output_prefix="cart_output_MinMaxLogMedK5_thinned"):
    """
    Performs Classification and Regression Tree (CART) analysis using scikit-learn.

    Args:
        file_path (str): Path to the CSV or Excel file containing the data.
        dependent_variable (str): Name of the column containing the dependent variable (stream class).
        independent_variables (list): List of column names containing the independent variables (basin characteristics).
        output_prefix (str, optional): Prefix for output files (e.g., confusion matrix, decision tree). Defaults to "cart_output_95_8".
    """

    try:
        # Load data from CSV or Excel file
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            data = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")

        # Prepare data for scikit-learn
        X = data[independent_variables]  # Independent variables
        y = data[dependent_variable]      # Dependent variable

        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)  # 70% training, 30% testing

        # Lower the leaf size to 5 to bring back the smaller categories
        dtree = DecisionTreeClassifier(max_depth=5, min_samples_leaf=5, random_state=42)

        # Train the model
        dtree.fit(X_train, y_train)

        # Make predictions on the testing set
        y_pred = dtree.predict(X_test)

        # Evaluate the model
        print("Classification Report:\n", classification_report(y_test, y_pred))
        conf_matrix = confusion_matrix(y_test, y_pred)
        print("Confusion Matrix:\n", conf_matrix)

        # Save confusion matrix to a CSV file
        conf_matrix_df = pd.DataFrame(conf_matrix)
        conf_matrix_df.to_csv(f"{output_prefix}_confusion_matrix.csv", index=False)

        # Visualize the Decision Tree (requires graphviz)
        dot_data = tree.export_graphviz(dtree, out_file=None,
                                        feature_names=independent_variables,
                                        class_names=[str(i) for i in sorted(data[dependent_variable].unique())],  # Class names as strings
                                        filled=True, rounded=True,
                                        special_characters=True)
        graph = graphviz.Source(dot_data)
        graph.render(f"{output_prefix}_decision_tree", view=False)  # Saves the tree as a PDF

        print(f"Confusion matrix saved to {output_prefix}_confusion_matrix.csv")
        print(f"Decision tree saved to {output_prefix}_decision_tree.pdf")


        # Feature Importance
        feature_importances = pd.DataFrame(dtree.feature_importances_,
                                            index = X_train.columns,
                                            columns=['importance']).sort_values('importance', ascending=False)
        print("\nFeature Importance:\n", feature_importances)

        # Save feature importances to a CSV file
        feature_importances.to_csv(f"{output_prefix}_feature_importances.csv")
        print(f"Feature importances saved to {output_prefix}_feature_importances.csv")


    except FileNotFoundError:
        print(f"Error: File not found at path: {file_path}")
    except KeyError as e:
        print(f"Error: Column name '{e}' not found in the file.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# file paths, variables table
if __name__ == "__main__":
    file_path = r"C:\Users\CN0401\OneDrive - MT\Grad School\Data\2025-12-18_CART_MinMaxLogMedK5.xlsx"  
    dependent_variable = "MinMaxLogMed7d_K5_merge"  
    independent_variables = ["SWE_April_daymetws", "tot_basin_slope_num", "WinterSumPrecipRatio_daymetws", "pctconif2001ws_num", "Aridity_daymetws", "clayws_num", "sandws_num", "bfiws_num"]  # Replace with your independent variable column names

    cart_analysis(file_path, dependent_variable, independent_variables)
