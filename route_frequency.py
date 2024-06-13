#import relevant libraries
import pandas as pd
import time

#convert GTFS data to dataframes
#GTFS from AT last updated 11 April
PATH = "/Users/chirantan/UoA MEnngSt/Research Project Z/Python/AT_GTFS/"

calendar_df = pd.read_csv(f"{PATH}calendar.txt")
trips_df = pd.read_csv(f"{PATH}trips.txt")
stop_times_df = pd.read_csv(f"{PATH}stop_times.txt")
route_df = pd.read_csv(f"{PATH}routes.txt")

def get_frequency(df):
    
    frequency_per_hour_df = df.groupby(["route_id", "service_id", "direction_id", "hour" ]).size().reset_index(name="frequency")
    frequency_per_hour_df = frequency_per_hour_df.sort_values(["route_id", "direction_id", "service_id"])
    
    mean_frequency_df = frequency_per_hour_df.groupby(["route_id"])["frequency"].mean().reset_index(name = "avg_frequency")

    mean_frequency_df["avg_frequency"] = mean_frequency_df["avg_frequency"].round(decimals=0)

    return frequency_per_hour_df, mean_frequency_df

service_id_exclude = []

for i, day in calendar_df.iterrows():
    x = day["monday"] + day["tuesday"] + day["wednesday"] + day["thursday"] + day ["friday"]
    if x < 4:
        service_id_exclude.append(day["service_id"])
        
print(service_id_exclude)

merged_df = pd.merge(trips_df, stop_times_df, how = "outer", on = "trip_id")

merged_df = merged_df.drop(merged_df[merged_df["service_id"].isin(service_id_exclude)].index)
merged_df = merged_df.drop(merged_df[merged_df["stop_sequence"] > 1].index)
merged_df = merged_df.drop(merged_df[merged_df["arrival_time"].str[:2].astype(int) >= 20].index)
merged_df = merged_df.drop(merged_df[merged_df["arrival_time"].str[:2].astype(int) < 6].index)

merged_df["hour"] = merged_df["arrival_time"].apply(lambda x: time.strptime(x, "%H:%M:%S").tm_hour)

routes_merged_df = pd.merge(merged_df, route_df, how = "outer", on = "route_id")

bus_df = routes_merged_df.drop(routes_merged_df[routes_merged_df["route_type"]!= 3].index)
metro_df = routes_merged_df.drop(routes_merged_df[routes_merged_df["route_type"] != 2].index)
ferry_df = routes_merged_df.drop(routes_merged_df[routes_merged_df["route_type"] != 4].index)

frq_hour_bus_df, frq_avg_bus_df = get_frequency(bus_df)
frq_hour_metro_df, frq_avg_metro_df = get_frequency(metro_df)
frq_hour_ferry_df, frq_avg_ferry_df = get_frequency(ferry_df)

with pd.ExcelWriter("AT_route_frequency.xlsx") as writer:
    frq_hour_bus_df.to_excel(writer, sheet_name = "Bus Frequency per hour")
    frq_avg_bus_df.to_excel(writer, sheet_name = "Bus Frequency AVG")
    frq_hour_metro_df.to_excel(writer, sheet_name = "Metro Frequency per hour")
    frq_avg_metro_df.to_excel(writer, sheet_name = "Metro Frequency AVG")
    frq_hour_ferry_df.to_excel(writer, sheet_name = "Ferry Frequency per hour")
    frq_avg_ferry_df.to_excel(writer, sheet_name = "Ferry Frequency AVG")