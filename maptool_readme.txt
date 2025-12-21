{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\froman\fcharset0 Times-Bold;\f1\froman\fcharset0 Times-Roman;\f2\fmodern\fcharset0 Courier;
}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;\red0\green0\blue233;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;\cssrgb\c0\c0\c93333;}
{\*\listtable{\list\listtemplateid1\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid1\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid1}
{\list\listtemplateid2\listhybrid{\listlevel\levelnfc0\levelnfcn0\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{decimal\}}{\leveltext\leveltemplateid101\'01\'00;}{\levelnumbers\'01;}\fi-360\li720\lin720 }{\listname ;}\listid2}
{\list\listtemplateid3\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid201\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid3}}
{\*\listoverridetable{\listoverride\listid1\listoverridecount0\ls1}{\listoverride\listid2\listoverridecount0\ls2}{\listoverride\listid3\listoverridecount0\ls3}}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\deftab720
\pard\pardeftab720\sa240\partightenfactor0

\f0\b\fs24 \cf0 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Live URL:
\f1\b0  
\f2\fs26 https://food.ryandenning.info
\f1\fs24  (Redirects to Streamlit) 
\f0\b Repository:
\f1\b0  GitHub / 
\f2\fs26 meetup-repository
\f1\fs24  (Public)\
\pard\pardeftab720\sa319\partightenfactor0

\f0\b \cf0 1. Secrets Configuration\
\pard\pardeftab720\sa240\partightenfactor0

\f1\b0 \cf0 If you re-deploy or reset the app, you must re-enter these in 
\f0\b Streamlit Dashboard > Settings > Secrets
\f1\b0 .\
\pard\pardeftab720\partightenfactor0
\cf0 Ini, TOML\
\
\pard\pardeftab720\partightenfactor0

\f2\fs26 \cf0 # Exact variable names required\
gmaps_api_key = "AIza..." \
app_password = "YourChosenPassword"\
\pard\pardeftab720\sa319\partightenfactor0

\f0\b\fs24 \cf0 2. Google Cloud Safety Limits\
\pard\tx220\tx720\pardeftab720\li720\fi-720\sa240\partightenfactor0
\ls1\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Console:
\f1\b0  {\field{\*\fldinst{HYPERLINK "https://console.cloud.google.com/google/maps-apis/quotas"}}{\fldrslt \cf3 \ul \ulc3 \strokec3 Google Cloud Console}}\
\ls1\ilvl0
\f0\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 APIs Used:
\f1\b0  Places API, Distance Matrix API, Geocoding API.\
\ls1\ilvl0
\f0\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Quotas Set:
\f1\b0  500 requests/day (per API) to prevent billing spikes.\
\pard\pardeftab720\sa319\partightenfactor0

\f0\b \cf0 3. How to Update the Code\
\pard\tx220\tx720\pardeftab720\li720\fi-720\sa240\partightenfactor0
\ls2\ilvl0
\f1\b0 \cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	1	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Edit 
\f2\fs26 app.py
\f1\fs24  on your computer.\
\ls2\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	2	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Upload the new file to your GitHub repository (drag & drop or git push).\
\ls2\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	3	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Streamlit detects the change and updates the live site automatically (usually within 10-30 seconds).\
\pard\pardeftab720\sa319\partightenfactor0

\f0\b \cf0 4. Troubleshooting\
\pard\tx220\tx720\pardeftab720\li720\fi-720\sa240\partightenfactor0
\ls3\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 "App does not exist"
\f1\b0 : Check if the Repo is still Public.\
\ls3\ilvl0
\f0\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Password skipped / API Key asked
\f1\b0 : Secrets are missing or named incorrectly.\
\ls3\ilvl0
\f0\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Map is blank
\f1\b0 : Check if Google Cloud billing is still active (even for free tier).\
}