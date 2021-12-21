from bs4 import BeautifulSoup
import requests
import pandas as pd
import streamlit as st
import time
import re
import plotly.express as px
from functools import partial
import geocoder
import bs4
from selenium import webdriver
from datetime import date
from datetime import timedelta

def get_destinations(web, tab_pos):
    """
    This function receives a soup object with the spanish Wikipedia page of
    the airport and the negative positions of the destination tables, and returns
    a list with all the destinations city, airports name and a dictionary with all airlines and
    the number of destinations they flight to. The table needs to have the following structure.
    +------------------+-------------------+-------------------+
    |City              |Airport Name       |Airlines           |
    +------------------+-------------------+-------------------+
    |Madrid            |Aeropuerto Adolfo S|Iberia, Air Europa,|
    |                  |uárez Madrid-Baraja| Vueling           |
    |                  |s                  |                   |
    +------------------+-------------------+-------------------+
    """
    aer=[]
    destinos = []
    aerolineas = dict()
    for i in tab_pos:
        for fila in web.find_all("table")[-i]:
            for columna in fila:
                if len(columna)>4:
                    if columna.find("td") is not None:
                        destinos.append(columna.find("td").text.replace("\n","").replace(" *","").replace("*",""))
                    if len(columna.find_all("td"))>2:
                        fil = columna.find_all("td")
                        aer.append(fil[-2].text.replace("\n",""))
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

def get_ubi(aeropuertos):
    """
    Returns the a list of latitude, longitude and country
    from a list of city name.
    """
    lat, lon = [],[]
    for aeropuerto in aeropuertos:
        d = geocoder.bing(aeropuerto, key=st.secrets["key"],
                          culture='es')
        if d.lat is not None and d.lng is not None:
            lat.append(d.lat)
            lon.append(d.lng)
    return lat, lon
def get_all_IATA():
    """
    Returns a pandas DataFrame with all airports IATA Code, airport name,
    city, state and country.
    """
    req = requests.get("https://es.wikipedia.org/wiki/Anexo:Aeropuertos_seg%C3%BAn_el_c%C3%B3digo_IATA")
    soup = BeautifulSoup(req.content)

    soup.find_all("table", {"class":"wikitable sortable"})
    respuesta= []
    for tabla in soup.find_all("table", {"class":"wikitable sortable"}):
        for subtabla in tabla.find_all("tbody"):
            for fila in subtabla:
                if len(fila) >3:
                    res= []
                    for col in fila:
                        if type(col)==bs4.element.Tag:
                            res.append(col.text.replace("\n","").replace("\xa0"," ").replace("[nota 1]",""))
                    respuesta.append(res)
    for n,linea in enumerate(respuesta):
        if "Código IATA" in linea or "Código DAC"in linea  :
            respuesta.pop(n)
    df = pd.DataFrame(respuesta, columns=['Codigo', 'Aeropuerto', 'Ciudad',"Provincia","Pais"])

    return df

def IATA_list(aer, destinos):
    """Returns a dictionary with all the matches from a airport list in a pandas with all IATA
    codes.
    """
    dic={}
    df = get_all_IATA()
    for aeropuerto, ciudad in zip(aer, destinos):
        d = df.loc[df["Aeropuerto"] == aeropuerto]
        if len(d["Codigo"])>0:
            if len(d["Codigo"])>1:
                for elem in d["Codigo"].items():
                    dic[ciudad+" | "+aeropuerto]= elem[1][:3]
            else:
                dic[ciudad+" | "+aeropuerto]= d["Codigo"].item()
    return dic

def flight_price(org, dest, fdate):
    web = "https://www.halconviajes.com/vuelos/availability/#/consolidator-family-fares?type=oneWay&numTravellers=1&pax0=30&"
    d = f"dep={fdate.day:02d}-{fdate.month:02d}-{fdate.year}&from={org}&to={dest}"
    driver = webdriver.Chrome()
    driver.get(web+d)
    time.sleep(8)

    soup = BeautifulSoup(driver.page_source)
    return soup.find("div", {"class":"text-l sm:text-xl text-white font-bold leading-none flex-shrink-0"}),web+d

st.set_page_config(layout="wide",page_title="Destination finder")

#Dictionary with some airports and its wikipedia page
aeropuertos = {"Barcelona":"https://es.wikipedia.org/wiki/Aeropuerto_Josep_Tarradellas_Barcelona-El_Prat",
               "Palma de Mallorca":"https://es.wikipedia.org/wiki/Aeropuerto_de_Palma_de_Mallorca",
               "Valencia":"https://es.wikipedia.org/wiki/Aeropuerto_de_Valencia",
               "Tenerife Sur":"https://es.wikipedia.org/wiki/Aeropuerto_de_Tenerife_Sur",
               "Madrid":"https://es.wikipedia.org/wiki/Aeropuerto_Adolfo_Su%C3%A1rez_Madrid-Barajas#Destinos_Nacionales",
               "Alicante":"https://es.wikipedia.org/wiki/Aeropuerto_de_Alicante-Elche_Miguel_Hern%C3%A1ndez",
               "Sevilla":"https://es.wikipedia.org/wiki/Aeropuerto_de_Sevilla",
               "Bilbao":"https://es.wikipedia.org/wiki/Aeropuerto_de_Bilbao"}

IATA_origen = {"Barcelona":"BCN", "Palma de Mallorca":"PMI","Valencia":"VLC",
"Tenerife Sur":"TFS","Madrid":"MAD","Sevilla":"SVQ","Bilbao":"BIO","Alicante":"ALC"}
#Title and destination selector.
col1, col2 = st.columns(2)
with col1:
    st.title("Destinos desde ")
with col2:
    option = st.selectbox("",sorted(aeropuertos))



content = requests.get(aeropuertos[option]) #Gets the airport page
soup = BeautifulSoup(content.content) #and create a soup object with the content

#The negative positon of the destination tables for each option
if option == "Valencia":
    tab_pos = [7,8]
elif option == "Tenerife Sur":
    tab_pos = [4,5]
elif option =="Madrid":
    tab_pos = [6,7]
elif option =="Barcelona" or option =="Sevilla" or option =="Bilbao":
    tab_pos = [9,10]
else: #Madrid, Palma de Mallorca,
    tab_pos = [2,3]

#Scraps the page and obtain all destinations and shows them
destinos,airport_names ,aerolineas = get_destinations(soup, tab_pos)
st.markdown(destination_rpr(destinos))

expander = st.expander("Mapa de destinos", False)

if expander.button("Generar mapa"): #Map and statistics generator button
    with st.spinner("Generando mapa (puede tardar un poco)..."):
            lat, lon = get_ubi(airport_names) #gets the lat and lon of the destinations
    expander.markdown("##### Mapa de destinos.")
    df = pd.DataFrame(list(zip(lat, lon)), columns =['lat', 'lon'])
    expander.map(df) #We plot the lat and lon into a map

c1, c2= st.columns((3,3)) #Number of different cities, airlines and countries
with c1:
    #Generates a pie chart with the number destinations that every airline flights to
    st.markdown("##### Price-Search")
    st.metric(label="Origen", value=option)
    IATA_dic= IATA_list(airport_names,destinos)
    destino = st.selectbox("Destino", sorted(IATA_dic))
    t1= date.today() + timedelta(days=7)
    t2 = t= date.today() + timedelta(days=180)
    fdate = st.date_input("Fecha del vuelo", value=t1, min_value=t1, max_value=t2)
    st.text("")
    if st.button("Buscar vuelo"):
        p,link = flight_price(IATA_origen[option], IATA_dic[destino], fdate)
        if p is None:
            p = "Precio no disponible"
            st.markdown(f"<h3 style='text-align: right; color: gray;'>{p}</h3>", unsafe_allow_html=True)
        else:
            p= "Precio estimado: "+p.text
            st.markdown(f"<h3 style='text-align: right; color: gray;'>{p}</h3>", unsafe_allow_html=True)
            st.write(f"Para reservar entra [aquí]({link})")

with c2:
    #Generates a pie chart with the number destinations that every airline flights to
    st.markdown("##### Aerolineas y número de rutas.")
    aer = pd.DataFrame(list(aerolineas.items()),columns = ["Aerolineas","Destinos"])
    aer["porcentaje"]= aer["Destinos"]/aer["Destinos"].sum()
    aer.loc[aer["porcentaje"] < 0.03, "Aerolineas"] = "Otras aerolineas"
    fig = px.pie(aer, values="Destinos", names="Aerolineas")
    st.plotly_chart(fig,use_container_width=True)
