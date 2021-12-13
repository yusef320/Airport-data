from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
import pandas as pd
import streamlit as st
import time
import re
import plotly.express as px
from functools import partial

def get_destintations(web, tab_pos):
    """
    This function receives a soup object with the spanish Wikipedia page of
    the airport and the negative positions of the destination tables, and returns
    a list with all the destinations and a dictionary with all airlines and
    the number of destinations they flight to.
    """
    aer=[]
    destinos = []
    aerolineas = dict()
    for i in tab_pos:
        for fila in web.find_all("table")[-i]:
            for columna in fila:
                if len(columna)>4:
                    if columna.find("td") is not None:
                        destinos.append(columna.find("td").text)
                    if len(columna.find_all("td"))>2:
                        var = columna.find_all("td")[-1].text.replace("/","").replace("(", "<").replace(")",">")
                        t = re.sub(r'<.*?>','', var)
                        t = t.replace("Estacional:", "").replace("estacional", "").replace("Estacional", "")
                        t = t.replace("Chárter:", "").replace(".", "")
                        for elemento in t.split("   "):
                            if elemento.strip() in aerolineas:
                                aerolineas[elemento.strip()]+=1
                            else:
                                aerolineas[elemento.strip()] = 1

    return destinos, aerolineas

def destination_rpr(destinos):
    """
    Creates a string representation for de destinations.
    """
    converted_list=[]
    for element in destinos:
        converted_list.append(element.strip())
    return " - ".join(sorted(converted_list))


def get_ubi(destinos):
    """
    Returns the a list of latitude, longitude and country
    from a list of city name.
    """
    geolocator = Nominatim(user_agent="destination_finder")
    lat, lon, pais = [],[],[]
    geocode = partial(geolocator.geocode, language="es")
    for destino in destinos:
        d= geocode(destino)
        lat.append(d.latitude)
        lon.append(d.longitude)
        if d.raw["display_name"].split(",")[-1] not in pais:
            pais.append(d.raw["display_name"].split(",")[-1])

    return lat, lon, pais


st.set_page_config(layout="wide",page_title="Destination finder")

#Title and destination selector.
col1, col2 = st.columns(2)
with col1:
    st.title("Destinos desde ")
with col2:
    option = st.selectbox("",("Tenerife Norte", "Palma de Mallorca","Valencia","Tenerife Sur","Madrid"))

#Dictionary with some airports and its wikipedia page
aeropuertos = {"Tenerife Norte":"https://es.wikipedia.org/wiki/Aeropuerto_de_Tenerife_Norte-Ciudad_de_La_Laguna",
               "Palma de Mallorca":"https://es.wikipedia.org/wiki/Aeropuerto_de_Palma_de_Mallorca",
               "Valencia":"https://es.wikipedia.org/wiki/Aeropuerto_de_Valencia",
               "Tenerife Sur":"https://es.wikipedia.org/wiki/Aeropuerto_de_Tenerife_Sur",
               "Madrid":"https://es.wikipedia.org/wiki/Aeropuerto_Adolfo_Su%C3%A1rez_Madrid-Barajas#Destinos_Nacionales"}

content = requests.get(aeropuertos[option]) #Gets the airport page
soup = BeautifulSoup(content.content) #and create a soup object with the content

#The negative positon of the destination tables for each option
if option == "Valencia":
    tab_pos = [8,7]
elif option == "Tenerife Sur":
    tab_pos = [5,4]
elif option =="Madrid":
    tab_pos = [6,7]
else:
    tab_pos = [2,3]

#Scraps the page and obtain all destinations and shows them
destinos, aerolineas = get_destintations(soup, tab_pos)
st.markdown(destination_rpr(destinos))

if st.button('Generar mapa y estadisticas'): #Map and statistics generator button

    st.markdown("##### Estadisticas.")
    c1, c2,c3 = st.columns(3) #Number of different cities, airlines and countries
    with c1:
        st.metric(label="Número de Ciudades", value=str(len(destinos)))
    with c2:
        st.metric(label="Número de aerolineas", value=str(len(aerolineas)))

    #Generates a pie chart with the number destinations that every airline flights to 
    st.markdown("##### Aerolineas y número de rutas.")
    aer = pd.DataFrame(list(aerolineas.items()),columns = ["Aerolineas","Destinos"])
    aer["porcentaje"]= aer["Destinos"]/aer["Destinos"].sum()
    aer.loc[aer["porcentaje"] < 0.009, "Aerolineas"] = "Otras aerolineas"
    fig = px.pie(aer, values="Destinos", names="Aerolineas")
    st.plotly_chart(fig,use_container_width=True)

    with st.spinner("Generando mapa (puede tardar un poco)..."):
            lat, lon, pais = get_ubi(destinos) #gets the lat and lon of the destinations

    with c3:
        st.metric(label="Número de Paises", value=str(len(pais)))

    st.markdown("##### Mapa de destinos.")
    df = pd.DataFrame(list(zip(lat, lon)), columns =['lat', 'lon'])
    st.map(df) #We plot the lat and lon into a map
