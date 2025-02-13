import csv, os, sys, re, uuid
import plotly.graph_objects as go
# import matplotlib.pyplot as fig
# Got an error with this library


# Testing the library
def main():
    if len(sys.argv) != 2:
        print("Missing file")
        sys.exit(1)
    transactions = Transactions(sys.argv[1])
    transactions.transactions("Hovedkategori")


# Class for calculating a budget from a .csv file
class Transactions:
    def __init__(self, file: str):
        # Name of the given file
        self.input_file = file
        #
        self.temporary_file = uuid.uuid4().hex + ".csv"
        # Cleans the data from the given file to show correct danish charachters
        if not self.cleanFile():
            print("Could not open file")
            return
        
        # Makes a dict for future use
        self.transaction_data = dict()


    # Calculates the data and groups it in with the "searchword" as grouping column
    def transactions(self, searchword: str):
        self.grouped_transactions = dict()

        # Opens the clean file
        with open(self.temporary_file, "r") as file:
            reader = csv.DictReader(file, delimiter=";")
            for row in reader:
                # Cleans the searchword for unneccessary long name (Not needed)
                clean_searchword = self.cleanString(row[searchword])
                # Checks if the category exists in the dict and adds the sum to the dict (Rounds the float to two decimals)
                if not clean_searchword in self.grouped_transactions:
                    self.grouped_transactions[clean_searchword] = round(float(''.join(row["Beløb"].split(".")).replace(",", ".")), 2)
                else:
                    self.grouped_transactions[clean_searchword] = round(self.grouped_transactions[clean_searchword] + round(float(''.join(row["Beløb"].split(".")).replace(",", ".")), 2), 2)
        
        # This new variable is only needed if possible to categorize by many different columns
        self.transaction_data[searchword] = self.grouped_transactions
        # Deletes the temporary file
        try:
            os.remove(self.temporary_file)
        except Exception as e:
            print(f"An error occured {e}")
        
        # Rearranging to put "Indtægter" first and "Andet" last
        try:
            indtægt = self.transaction_data["Hovedkategori"].pop("Indtægter")
            self.transaction_data["Hovedkategori"] = {"Indtægter": indtægt, **self.transaction_data["Hovedkategori"]}
        except:
            pass

        try:
            andet = self.transaction_data["Hovedkategori"].pop("Andet")
            self.transaction_data["Hovedkategori"].update({"Andet": andet})
        except:
            pass

        return self.transaction_data


    # The danish charachters are weirdly formatted
    def cleanFile(self):
        file_text = ""
        try:
            with open(self.input_file, "r") as file:
                for row in file:
                    file_text += row
        except FileNotFoundError:
            print("File not found")
            return False
        else:
            # Æ, ø, å
            file_text = file_text.replace("Ã¦", "æ").replace("Ã¸", "ø").replace("Ã¥", "å").replace("Ã©", "é")
            with open(self.temporary_file, "w") as file:
                file.write(file_text)
            return True
    

    # Sometimes the strings end with "... -Se medd." and this is removing it
    def cleanString(self, word: str):
        matches = re.search(r"^(.+?) *(?:-Se medd\.)*$", word, flags=re.IGNORECASE)
        return matches.group(1) if matches and matches.group(1) else word
    
    # Makes a plot
    def makePlot(self, dictionary: dict, filename: str):
        # Prepare data for the plot
        self.plot_items = list(dictionary.keys())
        self.plot_values = list(dictionary.values())
        
        # Create a bar chart using Plotly
        fig = go.Figure(data=[
            go.Bar(
                x=self.plot_items,
                y=self.plot_values,
                marker_color="green",
                name="Forbrug"
            )
        ])
        
        # Add layout and styling
        fig.update_layout(
            title={
                'text': "Forbrug fordelt på kategorier",
                'y': 0.9,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 15}
            },
            xaxis_title="Kategorier",
            yaxis_title="dkk",
            legend_title="Legend",
            xaxis=dict(tickangle=90),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        
        # Save the plot to a file (HTML)
        fig.write_html(filename)
        return


if __name__ == "__main__":
    main()