from bs4 import BeautifulSoup
import requests
import pandas as pd
import streamlit as st
import time
import re
import plotly.express as px
from functools import partial
import geocoder

def get_destinations(web, tab_pos):
    """
    This function receives a soup object with the spanish Wikipedia page of
    the airport and the negative positions of the destination tables, and returns
    a list with all the destinations city, airports name and a dictionary with all airlines and
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
                        fil = columna.find_all("td")
                        aer.append(fil[-2].text)
                        var = fil[-1].text.replace("/","").replace("(", "<").replace(")",">")
                        t = re.sub(r'<.*?>','', var)
                        t = t.replace("Estacional:", "").replace("estacional", "").replace("Estacional", "")
                        t = t.replace("Chárter:", "").replace(".", "")
                        for elemento in t.split("   "):
                            if elemento.strip() in aerolineas:
                                aerolineas[elemento.strip()]+=1
                            else:
                                aerolineas[elemento.strip()] = 1

    return destinos,aer ,aerolineas

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
    lat, lon = [],[]
    for destino in destinos:
        d = geocoder.bing(destino, key=st.secrets["key"],
                          culture='es')
        print(d.address)
        if d.lat is not None and d.lng is not None:
            lat.append(d.lat)
            lon.append(d.lng)
    return lat, lon


st.set_page_config(layout="wide",page_title="Destination finder")

#Title and destination selector.
col1, col2 = st.columns(2)
with col1:
    st.title("Destinos desde ")
with col2:
    option = st.selectbox("",("Barcelona", "Palma de Mallorca","Valencia","Tenerife Sur","Madrid"))

#Dictionary with some airports and its wikipedia page
aeropuertos = {"Barcelona":"https://es.wikipedia.org/wiki/Aeropuerto_Josep_Tarradellas_Barcelona-El_Prat",
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
elif option =="Barcelona":
    tab_pos = [9,10]
else:
    tab_pos = [2,3]

#Scraps the page and obtain all destinations and shows them
destinos,airport_names ,aerolineas = get_destinations(soup, tab_pos)
st.markdown(destination_rpr(destinos))

if st.button('Generar mapa y estadisticas'): #Map and statistics generator button

    st.markdown("##### Estadisticas.")
    
    c1, c2= st.columns(2) #Number of different cities, airlines and countries
    with c1:
        st.metric(label="Número de Ciudades", value=str(len(destinos)))
        st.metric(label="Número de aerolineas", value=str(len(aerolineas)))
    with c2:
        #Generates a pie chart with the number destinations that every airline flights to 
        st.markdown("##### Aerolineas y número de rutas.")
        aer = pd.DataFrame(list(aerolineas.items()),columns = ["Aerolineas","Destinos"])
        aer["porcentaje"]= aer["Destinos"]/aer["Destinos"].sum()
        aer.loc[aer["porcentaje"] < 0.009, "Aerolineas"] = "Otras aerolineas"
        fig = px.pie(aer, values="Destinos", names="Aerolineas")
        st.plotly_chart(fig,use_container_width=True)
    with st.spinner("Generando mapa (puede tardar un poco)..."):
            lat, lon = get_ubi(airport_names) #gets the lat and lon of the destinations


    st.markdown("##### Mapa de destinos.")
    df = pd.DataFrame(list(zip(lat, lon)), columns =['lat', 'lon'])
    st.map(df) #We plot the lat and lon into a map
