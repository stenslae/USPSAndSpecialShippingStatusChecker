from statusCheckPackage import siteScraping
import time

#################TODO: USER UPDATES THIS INFO
inputfile = "orders.csv"
datapath = r"\custom\user\path"
chromedriverpath = r"\chromedriver\path"
############################

# Read file and return array with carrier name, tracking number, and row number
data = siteScraping.inforead(inputfile)

#Create txt file to load error info onto
file = open('statusCheckErrors.txt', 'w')

print("Checking shipping statuses...")
# Check statuses of data
statuses = []
undelivered = []
for i in range(len(data)):
    delivered = siteScraping.checkstatus(data[i][0], data[i][1], data[i][2], file, datapath, chromedriverpath)
    status = [data[i][2], delivered]
    statuses.append(status)
    if 'Delivered' not in delivered:
        undelivered.append(data[i][2])
    print(f'Row {data[i][2]} has been checked')
    time.sleep(5)  # Delay between requests to avoid being blocked

print("All shipping statues have been checked.")
# Load arrays onto csv file to flag undelivered rows, and add row of statuses
siteScraping.infoupdate(inputfile, statuses, undelivered)

print(f"Check updated_{inputfile} for the shipping information and statusCheckErrors.txt for any errors.")
