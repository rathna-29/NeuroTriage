# inspect_dataset.py
# Prints a report about a CSV dataset. It only READS the file.
#
# How to run (from the NeuroTriage folder):
#   python notebooks\inspect_dataset.py dataset\your_file.csv

import sys
from pathlib import Path

import pandas as pd

# Columns with at most this many different values are treated as
# "possible label columns" and their counts are shown.
MAX_LABEL_VALUES = 12

# Words that suggest a column identifies a person or a recording.
ID_HINTS = ["id", "subject", "patient", "participant", "person", "record", "file", "session"]


def main():
    if len(sys.argv) != 2:
        print("Please give the CSV file name.")
        print("Example: python notebooks\\inspect_dataset.py dataset\\my_data.csv")
        return

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        print("Check the file name and that you are in the NeuroTriage folder.")
        return

    # Read the file. Reading can fail if the file is not a normal CSV.
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as error:
        print("Could not read the file as a CSV.")
        print("Technical detail:", error)
        return

    print("=" * 70)
    print("FILE:", path.name)
    print("=" * 70)

    # 1. Size
    print(f"\n1. SIZE\n   Rows: {len(df)}\n   Columns: {len(df.columns)}")

    # 2. Columns, types, missing values, number of different values
    print("\n2. COLUMNS (name | type | missing | different values)")
    if len(df.columns) > 60:
        print(f"   (showing the first 60 of {len(df.columns)} columns)")
    for name in list(df.columns)[:60]:
        missing = int(df[name].isna().sum())
        unique = int(df[name].nunique(dropna=True))
        print(f"   {str(name)[:40]:<40} | {str(df[name].dtype):<8} | {missing:>6} | {unique:>8}")

    # 3. Missing values overall
    total_missing = int(df.isna().sum().sum())
    print(f"\n3. MISSING VALUES IN TOTAL: {total_missing}")

    # 4. Columns that may identify a person or recording
    print("\n4. COLUMNS THAT MAY BE IDs (name suggests an identifier)")
    id_columns = [c for c in df.columns if any(h in str(c).lower() for h in ID_HINTS)]
    if id_columns:
        for c in id_columns:
            print(f"   {c}: {df[c].nunique(dropna=True)} different values")
    else:
        print("   None found by name. The dataset may have no subject IDs.")

    # 5. Possible label columns
    print(f"\n5. POSSIBLE LABEL COLUMNS (at most {MAX_LABEL_VALUES} different values)")
    found = False
    for c in df.columns:
        n = df[c].nunique(dropna=True)
        if 2 <= n <= MAX_LABEL_VALUES:
            found = True
            print(f"\n   Column: {c}")
            counts = df[c].value_counts(dropna=False)
            for value, count in counts.items():
                percent = 100 * count / len(df)
                print(f"      {str(value)[:30]:<30} {count:>8}  ({percent:.1f}%)")
    if not found:
        print("   None found.")

    # 6. Numeric summary (first 15 numeric columns)
    numeric = df.select_dtypes(include="number")
    print(f"\n6. NUMERIC COLUMNS: {numeric.shape[1]}")
    if numeric.shape[1] > 0:
        print("   Summary of the first 15 numeric columns:")
        print(numeric.iloc[:, :15].describe().T[["min", "mean", "max"]].round(3).to_string())

    # 7. First 3 rows
    print("\n7. FIRST 3 ROWS (first 10 columns)")
    print(df.iloc[:3, :10].to_string())

    print("\n" + "=" * 70)
    print("End of report. Nothing was changed.")


main()