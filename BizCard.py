import easyocr
from PIL import Image
import streamlit as st
from streamlit_option_menu import option_menu
from PIL import Image
import pandas as pd
import numpy as np
import pymysql
import re
import io


#Extracting images to text using easyocr
def image_to_text(path):
    image = Image.open(path)
    image_arr = np.array(image)
    reader = easyocr.Reader(['en'])
    text = reader.readtext(image=image_arr,detail=0)
    return text,image


#Classifying the text to specify column names
#Matching the contact number for specify image using regular expression
def is_valid_contact_number(text):
    return bool(re.match(r'\d{3}-\d{3}-\d{4}', text))

def extracted_texts(texts):
    extracted = {"NAME":[],"COMPANY NAME":[], "DESIGNATION":[], "CONTACT NO":[], "MAIL-ID":[], "WEBSITE":[], "ADDRESS":[],"PINCODE" :[]}

    for index,text in enumerate(texts):
        if index == 0:
            extracted["NAME"].append(text)
        elif index == 1:
            extracted["DESIGNATION"].append(text)
        elif (text.startswith("+")) or (index == 2 and is_valid_contact_number(text)) or (index == 4 and text.startswith("+")):
            contact = text.replace("-"," ") 
            extracted["CONTACT NO"].append(contact)
        elif "@" in text:
            extracted["MAIL-ID"].append(text)
        elif (text.startswith("wwW")) or (index ==4 and text.startswith("wwW")) or (text.startswith("www")) or (text.startswith("WWW")):
            website = text.replace("wwW","www").replace("WWW","www").lower()
            extracted["WEBSITE"].append(website)
        elif (text.startswith("TamilNadu")) or (index == 3 and text.isdigit()):
            extracted["PINCODE"].append(text)
        elif index == 7 or text.isalpha():
            company_name = text.replace(","," ")
            extracted["COMPANY NAME"].append(company_name) 
        else:
            remove_colon = re.sub(r'[,;]','',text)
            extracted["ADDRESS"].append(remove_colon) 

    if "global.com" in extracted["ADDRESS"]:
        extracted["WEBSITE"].append("global.com")
        extracted["ADDRESS"].remove("global.com")

    if "WWW" in extracted["COMPANY NAME"]:
        extracted["COMPANY NAME"].remove("WWW")

    if "Erode " in extracted["COMPANY NAME"]:
        extracted["COMPANY NAME"].remove("Erode ")
        extracted["ADDRESS"].append("Erode")

    for key,value in extracted.items():
        if len(value)>0:
            concatenate = " ".join(value)
            extracted[key] = [concatenate]
        else:
            value = "NA"
            extracted[key] = [value]
    
    return extracted


#Streamlit page
icon = Image.open("Business-card.png")
st.set_page_config(page_title="Extracting Business Card Data with OCR",
                   page_icon= icon,
                   layout="wide",
                   initial_sidebar_state="collapsed")

with st.sidebar:
    select = option_menu("Main Menu",("Home","Images Uploads","Updation and Deletion on Extracted Data"))

if select =="Home":
    st.sidebar.markdown("# Home")
    st.title("**Extracting Business Card Data with OCR**")
    col1,col2 = st.columns(2)
    with col1:
        st.markdown(" ")
        st.markdown(" ")
        st.markdown(" ")
        st.markdown(" ")
        st.markdown(" ")
        st.write("BizCardX project is to develope a Streamlit application that allows users to upload an image of a business card and extract relevant information from it using easyOCR.")
        st.markdown(" ")
        st.write("Easy OCR is a font-dependent printed character reader based on a template matching algorithm. It has been designed to read any kind of short text (part numbers, serial numbers, expiry dates, manufacturing dates, lot codes...)")
    with col2:
        st.markdown(" ")
        st.markdown(" ")
        st.image(icon)
    st.subheader("Technologies Used:")
    st.write("Python")
    st.write("EasyOCR")
    st.write("Streamlit")
    st.write("MySQL")


elif select == "Images Uploads":
    st.sidebar.markdown("# Images Uploads")
    st.title("EasyOCR - Extract Text from Images")
    image_path = st.file_uploader("Upload the Image",type=["png","jpeg","jpg"],label_visibility="visible")
    
    if image_path is not None:
        st.image(image_path,width=700)
        text_upload,image_upload = image_to_text(image_path)

        text = extracted_texts(text_upload)
        st.success("Extracted data uploaded successfully")

        df = pd.DataFrame(text)

        #Converting image into binary format
        Image_bytes = io.BytesIO()
        image_upload.save(Image_bytes,format = "PNG")
        image_data = Image_bytes.getvalue()

        #Creating Dictionary
        data = {"IMAGE":[image_data]}

        #Concating image format and text to dataframe
        df_1 = pd.DataFrame(data)
        concat_df = pd.concat([df,df_1],axis =1)
        st.dataframe(concat_df)
        
        button = st.button("Upload to MySQL")

        if button:
            #Inserting the collected DataFrame to Mysql database
            myconn = pymysql.connect(host='127.0.0.1',user='root',passwd='Tspjgoge@5',database='bizcard')
            cur = myconn.cursor()

            def classify_texts():
                try:
                    create_query = '''create table if not exists card_details (NAME varchar(50),
                                                                COMPANY_NAME varchar(50),
                                                                DESIGNATION varchar(50),
                                                                CONTACT_NO varchar(50), 
                                                                MAIL_ID varchar(50), 
                                                                WEBSITE text,
                                                                ADDRESS varchar(50),
                                                                PINCODE varchar(50),
                                                                IMAGE LONGBLOB)'''
                                                                    
                    cur.execute(create_query)
                    myconn.commit()
                    print("Card Detail table created successfully")
                except pymysql.err.OperationalError as e:
                    print(f"Error creating table: {e}")

            classify_texts()

            cur = myconn.cursor()
            sql = '''INSERT INTO card_details(NAME,COMPANY_NAME,DESIGNATION,CONTACT_NO,MAIL_ID,WEBSITE,ADDRESS,PINCODE,IMAGE) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
            for row in concat_df.values.tolist():
                cur.execute(sql,row)
            myconn.commit() 

            st.success("Data Uploaded Successfully")

            #Displaying the dataframe from mysql
            select_query = "SELECT * from card_details"
            cur.execute(select_query)
            table = cur.fetchall()
            myconn.commit()

            table_df = pd.DataFrame(table,columns=("NAME","COMPANY_NAME","DESIGNATION","CONTACT_NO","MAIL_ID","WEBSITE","ADDRESS","PINCODE","IMAGE"))
            st.dataframe(table_df)

elif select == "Updation and Deletion on Extracted Data":
    st.sidebar.markdown("# Updation and Deletion on Extracted Data")
    st.title("EasyOCR-Modifying the Text using the Extracted Data")

    tab1,tab2 = st.tabs(["Updates","Delete"])

    with tab1:
        #Connecting the database
        myconn = pymysql.connect(host='127.0.0.1',user='root',passwd='Tspjgoge@5',database='bizcard')
        cur = myconn.cursor()
        
        select_query = "SELECT * from card_details"
        cur.execute(select_query)
        table = cur.fetchall()
        myconn.commit()

        table_df = pd.DataFrame(table,columns=("NAME","COMPANY_NAME","DESIGNATION","CONTACT_NO","MAIL_ID","WEBSITE","ADDRESS","PINCODE","IMAGE"))

        select_name = st.selectbox("Select the name",table_df["NAME"])
        
        df_2 = table_df[table_df["NAME"]==select_name]
        df_3 = df_2.copy()

        col1,col2 = st.columns(2)
        with col1:
            up_name = st.text_input("NAME",df_2["NAME"].unique()[0])
            up_coname = st.text_input("COMPANY_NAME",df_2["COMPANY_NAME"].unique()[0])
            up_desi = st.text_input("DESIGNATION",df_2["DESIGNATION"].unique()[0])
            up_cont = st.text_input("CONTACT_NO",df_2["CONTACT_NO"].unique()[0])
            up_mail = st.text_input("MAIL_ID",df_2["MAIL_ID"].unique()[0])

            df_3["NAME"] = up_name
            df_3["COMPANY_NAME"] = up_coname
            df_3["DESIGNATION"] = up_desi
            df_3["CONTACT_NO"] = up_cont
            df_3["MAIL_ID"] = up_mail
        
        with col2:
            up_web = st.text_input("WEBSITE",df_2["WEBSITE"].unique()[0])
            up_add = st.text_input("ADDRESS",df_2["ADDRESS"].unique()[0])
            up_pin = st.text_input("PINCODE",df_2["PINCODE"].unique()[0])
            up_ima = st.text_input("IMAGE",df_2["IMAGE"].unique()[0])

            df_3["WEBSITE"] = up_web
            df_3["ADDRESS"] = up_add
            df_3["PINCODE"] = up_pin
            df_3["IMAGE"] = up_ima

        st.button("Update")
        st.dataframe(df_3)
    
    with tab2:  
        st.dataframe(df_3)
        col_to_delete = st.radio("Select the column to delete",df_3.columns)
        
        def value_to_delete():
            if col_to_delete == "NAME":
                return df_3["NAME"].unique()[0]
            elif col_to_delete == "COMPANY_NAME":
                return df_3["COMPANY_NAME"].unique()[0]
            elif col_to_delete == "DESIGNATION":
                return df_3["DESIGNATION"].unique()[0]
            elif col_to_delete == "CONTACT_NO":
                return df_3["CONTACT_NO"].unique()[0]
            elif col_to_delete == "MAIL_ID":
                return df_3["MAIL_ID"].unique()[0]
            elif col_to_delete == "WEBSITE":
                return df_3["WEBSITE"].unique()[0]
            elif col_to_delete == "COMPANY_NAME":
                return df_3["COMPANY_NAME"].unique()[0]
            elif col_to_delete == "ADDRESS":
                return df_3["ADDRESS"].unique()[0]
            elif col_to_delete == "PINCODE":
                return df_3["PINCODE"].unique()[0]
            else:
                return df_3["IMAGE"].unique()[0]

        value = value_to_delete()
        st.toggle(value)

        if st.button("Delete"):
            value_to_delete = value_to_delete()  # Get the value to delete
            df_3[col_to_delete] = df_3[col_to_delete].apply(lambda x: np.nan if x == value_to_delete else x)
            st.success("Data deleted successfully!")

        st.dataframe(df_3)
