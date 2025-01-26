import csv, os, sys, re, uuid
# import matplotlib.pyplot as fig
import plotly.graph_objects as go

def main():
    if len(sys.argv) != 2:
        print("Missing file")
        sys.exit(1)
    transactions = Transactions(sys.argv[1])
    transactions.transactions("Hovedkategori")

class Transactions:
    def __init__(self, file: str):
        self.input_file = file
        self.new_file = uuid.uuid4().hex + ".csv"
        if not self.cleanFile():
            print("Could not open file")
            return
        
#        self.pic_name = "Hello.html"
        self.transaction_data = dict()
#        for group in groups:
#            self.transactions(group)
#            self.makePlot(self.transaction_data[group], self.pic_name)
            
    def transactions(self, searchword: str):
        self.grouped_transactions = dict()

        with open(self.new_file, "r") as file:
            reader = csv.DictReader(file, delimiter=";")
            for row in reader:
                clean_searchword = self.cleanString(row[searchword])
                if not clean_searchword in self.grouped_transactions:
                    self.grouped_transactions[clean_searchword] = round(float(''.join(row["Beløb"].split(".")).replace(",", ".")), 2)
                else:
                    self.grouped_transactions[clean_searchword] = round(self.grouped_transactions[clean_searchword] + round(float(''.join(row["Beløb"].split(".")).replace(",", ".")), 2), 2)
        
        self.transaction_data[searchword] = self.grouped_transactions
        try:
            os.remove(self.new_file)
        except Exception as e:
            print(f"An error occured {e}")
        
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
            file_text = file_text.replace("Ã¦", "æ").replace("Ã¸", "ø").replace("Ã¥", "å").replace("Ã©", "é")
            with open(self.new_file, "w") as file:
                file.write(file_text)
            return True
    
    def cleanString(self, word: str):
        matches = re.search(r"^(.+?) *(?:-Se medd\.)*$", word, flags=re.IGNORECASE)
        return matches.group(1) if matches and matches.group(1) else word
    
#    def makePlot(self, dictionary: dict, filename: str):
        self.plot_items = list()
        self.plot_values = list()
        for kwarg in dictionary:
            self.plot_items.append(kwarg)
            self.plot_values.append(dictionary[kwarg])
        fig.bar(self.plot_items, self.plot_values, color="g", width=0.72, label="Forbrug")
        fig.xticks(rotation = 90)
        fig.xlabel("Kategorier")
        fig.ylabel("dkk")
        fig.title(f"Forbrug fordelt på kategorier", fontsize = 15)
        fig.tight_layout()
        fig.legend()
        fig.savefig(filename)
        return filename
    
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