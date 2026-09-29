"""YouTube - latest uploads per channel from the channel page's own data.

YouTube's per-channel Atom feed (``/feeds/videos.xml?channel_id=<id>``)
served every source here until 2026-09, when the endpoint started
answering 404 for every channel - including the URL each channel page
still advertises in its own markup. The uploads are read from the
``/videos`` tab instead: the page embeds ``ytInitialData`` with the same
~30 most recent uploads the feed used to carry. Upload times only reach
the page as relative text ("3 hours ago"), so ``pub_date`` is
approximate - fine for card ordering, which is all it feeds.
"""

import asyncio
import json
import re
import time
from typing import Any

from ..fetch import NewsFetchError, fetch_text
from ..registry import register
from ..schemas import NewsItem
from ..youtube_extra import YOUTUBE_EXTRA

_CHANNELS: list[tuple[str, str, str]] = [  # (channel_id, source_id, display)
    ("UCBJycsmduvYEL83R_U4JriQ", "youtube-mkbhd", "Marques Brownlee"),
    ("UCHnyfMqiRRG1u-2MsSQLbXA", "youtube-veritasium", "Veritasium"),
    ("UCX6OQ3DkcsbYNE6H8uQQuVA", "youtube-mrbeast", "MrBeast"),
    ("UCsXVk37bltHxD1rDPwtNM8Q", "youtube-kurzgesagt", "Kurzgesagt"),
    ("UC16niRr50-MSBwiO3YDb3RA", "youtube-bbcnews", "BBC News"),
    ("UCqnbDFdCpuN8CMEg0VuEBqA", "youtube-nytimes", "The New York Times"),
    ("UCupvZG-5ko_eiXAupbDfxWw", "youtube-cnn", "CNN"),
    ("UCvJJ_dzjViJCoLf5uKUTwoA", "youtube-cnbc", "CNBC"),
    ("UCUMZ7gohGI9HcU9VNsr2FJQ", "youtube-bloomberg", "Bloomberg"),
    ("UCsooa4yRKGN_zEE8iknghZA", "youtube-ted", "TED"),
    ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "youtube-electroboom", "ElectroBOOM"),
    ("UC2C_jShtL725hvbm1arSV9w", "youtube-cgpgrey", "CGP Grey"),
    ("UCsT0YIqwnpJCM-mx7-gSA4Q", "youtube-tedx", "TEDx Talks"),
    ("UCiWLfSweyRNmLpgEHekhoAg", "youtube-espn", "ESPN"),
    ("UCXuqSBlHAE6Xw-yeJA0Tunw", "youtube-linus", "Linus Tech Tips"),
    # batch 2 - broader categories
    ("UCq-Fj5jknLsUf-MWSy4_brA", "youtube-tseries", "T-Series"),
    ("UC295-Dw_tDNtZXFeAPAW6Aw", "youtube-5mc", "5-Minute Crafts"),
    ("UCpEhnqL0y41EpW2TvWAHD7Q", "youtube-setindia", "SET India"),
    ("UCJ5v_MCY6GNUBTO8-D3XoAg", "youtube-wwe", "WWE"),
    ("UCk8GzjMOrta8yxDcKfylJYw", "youtube-kidsdiana", "Kids Diana Show"),
    ("UCbCmjCuTUZos6Inko4u57UQ", "youtube-cocomelon", "Cocomelon"),
    ("UCpVm7bg6pXKo1Pr6k5kxG9A", "youtube-natgeo", "National Geographic"),
    ("UCYzPXprvl5Y-Sf0g4vX-m6g", "youtube-jacksepticeye", "jacksepticeye"),
    ("UC-lHJZR3Gqxm24_Vd_AJ5Yw", "youtube-pewdiepie", "PewDiePie"),
    ("UCJ24N4O0bP7LGLBDvye7oCA", "youtube-mattdavella", "Matt D'Avella"),
    ("UC8butISFwT-Wl7EV0hUK0BQ", "youtube-freecodecamp", "freeCodeCamp"),
    ("UC4xKdmAXFh4ACyhpiQ_3qBw", "youtube-tomscott", "TechLead"),
    ("UCftwRNsjfRo08xYE31tkiyw", "youtube-wired", "WIRED"),
    ("UCsBjURrPoezykLs9EqgamOA", "youtube-fireship", "Fireship"),
    ("UC0v-tlzsn0QZwJnkiaUSJVQ", "youtube-fitnessblender", "REACT"),
    ("UCe0TLA0EsQbE-MjuHXevj2A", "youtube-athleanx", "ATHLEAN-X"),
    ("UCoxcjq-8xIDTYp3uz647V5A", "youtube-numberphile", "Numberphile"),
    ("UCYO_jab_esuFRV4b17AJtAw", "youtube-3blue1brown", "3Blue1Brown"),
    ("UC7_gcs09iThXybpVgjHZ_7g", "youtube-pbsspacetime", "PBS Space Time"),
    ("UCG8rbF3g2AMX70yOd8vqIZg", "youtube-lockpickinglawyer", "Logan Paul"),
    ("UC6nSFpj9HTCZ5t-N3Rm3-HA", "youtube-vsauce", "Vsauce"),
    ("UCsvn_Po0SmunchJYOWpOxMg", "youtube-videogamedunkey", "videogamedunkey"),
    ("UCtinbF-Q-fVthA0qrFQTgXQ", "youtube-casey", "Casey Neistat"),
    # batch 3 - to 100 channels
    ("UCLXo7UDZvByw2ixzpQCufnA", "youtube-vox", "Vox"),
    ("UCX6b17PVsYBQ0ip5gyeme-Q", "youtube-crashcourse", "CrashCourse"),
    ("UCVYamHliCI9rw1tHR1xbkfw", "youtube-dave2d", "Dave2D"),
    ("UCWJ2lWNubArHWmf3FIHbfcQ", "youtube-nba", "NBA"),
    ("UCa-ckhlKL98F8YXKQ-BALiw", "youtube-grahamstephan", "Graham Stephan"),
    ("UC7_YxT-KID8kRbqZo7MyscQ", "youtube-markiplier", "Markiplier"),
    ("UCn8zNIfYAQNdrFRrr8oibKw", "youtube-vice", "VICE"),
    ("UC2ri4rEb8abnNwXvTjg5ARw", "youtube-khanacademy", "Khan Academy"),
    ("UCsTcErHg8oDvUnTzoqsYeNw", "youtube-unboxtherapy", "Lew Later"),
    ("UCJdl3Paao2f3ha5JXMYUCIA", "youtube-nfl", "NFL"),
    ("UCGy7SkBjcIAgTiwkXEtPnYg", "youtube-andreijikh", "Andrei Jikh"),
    ("UCAW-NpUFkMyCNrvRSSGIvDQ", "youtube-ninja", "Ninja"),
    ("UCbbS1GE942k3UVqpLklyhIA", "youtube-dwnews", "DW Podcasts"),
    ("UCZYTClx2T1of7BRZ86-8fow", "youtube-scishow", "SciShow"),
    ("UCWFKCr40YwOZQx8FHU_ZqqQ", "youtube-jerryrig", "JerryRigEverything"),
    ("UCpcTrCXblq78GZrTUTLWeBw", "youtube-fifa", "FIFA"),
    ("UChfo46ZNOV-vtehDc25A1Ug", "youtube-aliabdaal", "Ali Abdaal"),
    ("UCS5Oz6CHmeoF7vSad0qqXfw", "youtube-dantdm", "DanTDM"),
    ("UCfiwzLy-8yKzIbsmZTzxDgw", "youtube-aljazeera", "Al Jazeera"),
    ("UCUHW94eEFW7hkUMVaZz4eDg", "youtube-minutephysics", "MinuteEarth"),
    ("UCMiJRAwDNSNzuYeN2uWa0pA", "youtube-mrwhosetheboss", "Mrwhosetheboss"),
    ("UCPQDDlGe7lbgmEJ0ge7a_JA", "youtube-ufc", "UFC"),
    ("UCFCEuCsyWP0YkP3CZ3Mr01Q", "youtube-plainbagel", "The Plain Bagel"),
    ("UCqECaJ8Gagnn7YCbPEzWH6g", "youtube-taylorswift", "Taylor Swift"),
    ("UCkFclpi8U9VJjfxLYoms7Aw", "youtube-skynews", "Mornings With Ridge & Frost"),
    ("UC8VkNBOwvsTlFjoSnNSMmxw", "youtube-smartereveryday", "SmarterEveryDay"),
    ("UCOuGATIAbd2DvzJmUgXn2IQ", "youtube-networkchuck", "NetworkChuck"),
    ("UCd8iY-kEHtaB8qt8MH--zGw", "youtube-formula1", "Ferrari"),
    ("UC9WQRw8jgJhag-vkDNTDMRg", "youtube-coffeezilla", "Coffee Break"),
    ("UCOmHUn--16B90oW2L6FRR3A", "youtube-blackpink", "YG ENTERTAINMENT"),
    ("UChqUTb7kYRX8-EiaN3XFrSQ", "youtube-reuters", "Reuters"),
    ("UCY1kMZp36IQSyNx_9h4mpCg", "youtube-markrober", "CrunchLabs"),
    ("UCtuO2h6OwDueF7h3p8DYYjQ", "youtube-theo", "Theo"),
    ("UCjVd6vTuoAYLFYvX5TSK1aA", "youtube-dazn", "GOAL"),
    ("UCnjgxChqYYnyoqO4k_Q1d6Q", "youtube-doac", "The Diary Of A CEO"),
    ("UCg40OxZ1GYh3u3jBntB6DLg", "youtube-forbes", "Forbes"),
    ("UC1D3yD4wlPMico0dss264XA", "youtube-nilered", "NileBlue"),
    ("UCbfYPyITQ-7l4upoX8nvctg", "youtube-twominutepapers", "Two Minute Papers"),
    ("UCDGmojLIoWpXok597xYo8cg", "youtube-billieeilish", "Billie Eilish"),
    ("UCwukDJWDHn4JW2aHps1ZCvA", "youtube-today", "TODAY"),
    ("UCEIwxahdLz7bap-VDs9h35A", "youtube-stevemould", "Steve Mould"),
    ("UCEdvpU2pFRCVqU6yIPyTpMQ", "youtube-marshmello", "Marshmello"),
    ("UCBi2mrWuNuyYy4gbM6fU18Q", "youtube-abcnews", "ABC News"),
    ("UCIwFjwMjI0y7PDBVEO9-bkQ", "youtube-justinbieber", "Justin Bieber"),
    ("UChDKyKQ59fYz3JO2fl0Z6sg", "youtube-nbcnews", "TODAY"),
    ("UCYNbYGl89UUowy8oXkipC-Q", "youtube-drbecky", "Dr. Becky"),
    ("UC0C-w0YjGpqDXGB8IHb662A", "youtube-edsheeran", "Ed Sheeran"),
    ("UCMliswJ7oukCeW35GSayhRA", "youtube-wsj", "WSJ News"),
    ("UCbpMy0Fg74eXXkvxJrtEn3w", "youtube-bonappetit", "Bon Appétit"),
    ("UCdsOTr6SmDrxuWE7sJFrkhQ", "youtube-bbcearth", "BBC Earth"),
    ("UCUAg71CJEvFdOnujmep1Svw", "youtube-joshuaweissman", "Joshua Weissman"),
    ("UCIALMKvObZNtJ6AmdCLP7Lg", "youtube-bloombergbiz", "Bloomberg Television"),
    ("UCsooa4yRKGN_zEE8iknghZA", "youtube-teded", "TED-Ed"),
    ("UCPD_bxCRGpmmeQcbe2kpPaA", "youtube-hotones", "First We Feast"),
    ("UC2D2CMWXMOVWx7giW1n3LIg", "youtube-hubermanlab", "Andrew Huberman"),
    ("UCY30JRSgfhYXA6i6xX1erWg", "youtube-smosh", "Smosh"),
    # batch 4 - scale-up
    ("UCdBK94H6oZT2Q7l0-b0xmMg", "youtube-linustechtips", "ShortCircuit"),
    ("UC1IQIspOkCeV3WnYm32SBFQ", "youtube-austinevans", "This Is"),
    ("UCCDU1fsmgvWljcW2aodfJsA", "youtube-arstechnica", "arstechnica"),
    ("UCL8Nxsa1LB9DrMTHtt3IKiw", "youtube-cnet", "Mashable"),
    ("UCddiUEpeqJcYeBxX1IVBKvQ", "youtube-theverge", "TheVerge"),
    ("UC-6OW5aJYBFM33zXQlBKPNA", "youtube-engadget", "engadget"),
    ("UCCjyq_K1Xwfg8Lndy7lKMpA", "youtube-techcrunch", "TechCrunch"),
    ("UCmOdED66QPe_Z2IR1F17COg", "youtube-hardwarecanucks", "hardwarecanucks"),
    ("UCgGw5WSITWvDISNjydXPW3A", "youtube-gamersnexus", "gamersnexus"),
    ("UCgzg_f5HC6EnY-9q5Px1Q-g", "youtube-codebullet", "CodeBullet"),
    ("UCQALLeQPoZdZC4JNUboVEUg", "youtube-sentdex", "Jabrils"),
    ("UCTrAO0TDCldnYUN3BkLmGcw", "youtube-b001", "b001"),
    ("UCb3ZMYnkBUxR8f_9lx2PoRA", "youtube-brancheducation", "BranchEducation"),
    (
        "UC_vRow-5SacIB2W-35XHK7w",
        "youtube-thiojoe",
        "Actual School: What They Should've Taught You",
    ),
    ("UC7btqG2Ww0_2LwuQxpvo2HQ", "youtube-codewithharry", "ProgrammingWithHarry"),
    ("UCoQ8B21RIncI9NWLr2d2Y_w", "youtube-techworldwithnana", "Nana Janashia"),
    ("UCWv7vMbMWH4-V0ZXdmDpPBA", "youtube-programmingwithmosh", "programmingwithmosh"),
    ("UC29ju8bIPH5as8OGnQzwJyA", "youtube-traversymedia", "traversymedia"),
    ("UCFbNIlppjAuEX4znoulh0Cw", "youtube-webdevsimplified", "WebDevSimplified"),
    ("UCSJbGtTlrDami-tDGPUV9-w", "youtube-academind", "academind"),
    ("UCJZv4d5rbIKd4QHMPkcABCw", "youtube-kevinpowell", "kevinpowell"),
    ("UCZgt6AzoyjslHTC9dz0UoTw", "youtube-bytebytego", "bytebytego"),
    ("UCVhQ2NnY5Rskt6UjCUkJ_DA", "youtube-arjancodes", "ArjanCodes"),
    ("UC0SNGrU20N1Q0SPWimGu7gQ", "youtube-codeaesthetic", "Malloc"),
    ("UCOSojkwOYL-9q9LzzERAihA", "youtube-devopstoolkit", "DevOps Paradox"),
    ("UCLA_DiR1FfKNvjuUpBHmylQ", "youtube-nasa", "nasa"),
    ("UCtI0Hodo5o5dUb67FeUjDeA", "youtube-spacex", "SpaceX"),
    ("UCZYTClx2T1of7BRZ86-8fow", "youtube-scishowspace", "SciShowSpace"),
    ("UCxzC4EngIsMrPmbm6Nxvb-A", "youtube-scottmanley", "ScottManley"),
    ("UCgRT6t_TqE_L8ggQ3WKyDog", "youtube-coolworldslab", "Cool Worlds Podcast"),
    ("UCpMcsdZf2KkAnfmxiq2MfMQ", "youtube-arvinash", "arvinash"),
    ("UCLneiIR_ivuWYuJzGVRoZLA", "youtube-parthgchannel", "ParthGChannel"),
    (
        "UCFk__1iexL3T5gvGcMpeHNA",
        "youtube-lookingglassuniverse",
        "LookingGlassUniverse",
    ),
    ("UCRz_3xzO7iPP6tB07TIL5ZQ", "youtube-scienceasylum", "Nick Lucid"),
    ("UCHqDTfIX-0DGaHlWvv6JZCw", "youtube-tomscottgo", "Lateral with Tom Scott"),
    (
        "UCh6aABYN8fg7VsFcSUZkC1A",
        "youtube-historyoftheuniverse",
        "HistoryoftheUniverse",
    ),
    ("UCk5RbHuAyBsvqxmKf9yyomQ", "youtube-kurtjmac", "ConeDodger240"),
    ("UC176GAQozKKjhz62H8u9vQQ", "youtube-realengineering", "Real Science"),
    (
        "UCMOqf8ab-42UUQIdVoKwjlQ",
        "youtube-practicalengineeringchannel",
        "PracticalEngineeringChannel",
    ),
    ("UC2bkHVIDjXS7sgrgjFtzOXQ", "youtube-engineerguyvideo", "Engineerguyvideo"),
    (
        "UCZYvU-ZWbgl1rJv0trRk_fA",
        "youtube-tomstantonengineering",
        "TomStantonEngineering",
    ),
    ("UCNlBbEpwffgWefkbRm73xxQ", "youtube-stuffmadehere", "StuffMadeHere"),
    ("UC2DjFE7Xf11URZqWBigcVOQ", "youtube-bigclivedotcom", "EEVblog"),
    ("UCVSHXNNBitaPd5lYz48--yg", "youtube-techingredients", "TechIngredients"),
    ("UCI4I6ldZ0jWe7vXpUVeVcpg", "youtube-nighthawkinlight", "Household Hacker"),
    ("UCV5vCi3jPJdURZwAOO_FNfQ", "youtube-thethoughtemporium", "TheThoughtEmporium"),
    ("UCrRttZIypNTA1Mrfwo745Sg", "youtube-smithsonianchannel", "Paramount Plus"),
    ("UCrNnk0wFBnCS1awGjq_ijGQ", "youtube-pbs", "PBS"),
    ("UC6107grRI4m0o2-emgoDnAA", "youtube-besmart", "SmarterEveryDay"),
    ("UCUHW94eEFW7hkUMVaZz4eDg", "youtube-minuteearth", "minutephysics"),
    ("UCkyfHZ6bY2TjqbJhiH8Y2QQ", "youtube-thebrainscoop", "TheBrainScoop"),
    ("UCvBqzzvUBLCs8Y7Axb-jZew", "youtube-sixtysymbols", "sixtysymbols"),
    ("UCtwKon9qMt5YLVgQt1tvJKg", "youtube-periodicvideos", "Objectivity"),
    ("UC52X5wxOL_s5yw0dQk7NtgA", "youtube-associatedpress", "AssociatedPress"),
    ("UC-SJ6nODDmufqBzPBwCvYvQ", "youtube-cbsnews", "CBS Mornings"),
    ("UC8p1vwvWtl6T73JiExfWs1g", "youtube-cbseveningnews", "CBS News"),
    ("UCnyCrv8b7bu0oWFXGyHaPzg", "youtube-trtworld", "TRTWorld"),
    ("UCTrQ7HXWRRxr7OsOtodr2_w", "youtube-channel4news", "channel4news"),
    ("UCXBD5iG5cr4ZYZ99K-fmDHg", "youtube-ndtv", "ndtv"),
    ("UCef1-8eOpJgud7szVPlZQAQ", "youtube-firstpost", "CNN-News18"),
    ("UCoUxsWakJucWg46KW5RsvPw", "youtube-financialtimes", "FinancialTimes"),
    ("UC2s0uKOc2WgB9eGta7cUUEA", "youtube-pbsnewshour", "Washington Week PBS"),
    ("UCzuqE7-t13O4NIDYJfakrhw", "youtube-democracynow", "democracynow"),
    ("UCPWXiRWZ29zrxPFIQT7eHSA", "youtube-thehill", "thehill"),
    ("UCgjtvMmHXbutALaw9XzRkAg", "youtube-politico", "politico"),
    ("UCbH66CA-esWX4EBCvsXQtwQ", "youtube-axios", "axios"),
    ("UCtB4ylCuQW0ue8ACIsHmD1w", "youtube-semafor", "semafor"),
    ("UCTkXRDQl0luXxVQrRQvWS6w", "youtube-dream", "dream"),
    ("UCPDTrtVU72FgD6QHVY2d04Q", "youtube-georgenotfound", "GeorgeNotFound"),
    ("UC5BqtRANoqrdMA0lEnZgOOg", "youtube-tommyinnit", "Shut Up I'm Talking"),
    ("UCKQ-wNdh0kO5qnpPfXa2hjQ", "youtube-ranboo", "Ranboo"),
    ("UCotpsO5-apJVUfsiieSb71g", "youtube-valkyrae", "Wine About It"),
    ("UC-t9T8WvzN9Kfnp-WL5hOUw", "youtube-pokimane", "Sweet n Sour Podcast"),
    ("UCEe1XYzORRRcwOUYNR0QwYw", "youtube-daniellabelle", "DanielLaBelle"),
    ("UCRijo3ddMTht_IHyNSNXpNQ", "youtube-dudeperfect", "dudeperfect"),
    ("UCh5mLn90vUaB1PbRRx_AiaA", "youtube-sidemen", "sidemen"),
    ("UCDogdKl7t7NHzQ95aEwkdMw", "youtube-moresidemen", "MoreSidemen"),
    ("UCVtFOytbRpEvzLjvqGG5gxQ", "youtube-ksi", "KSI"),
    ("UC5_IT4-XpinnvNQwM1e15eQ", "youtube-w2s", "W2S"),
    ("UCWZmCMB7mmKWcXJSIPRhzZw", "youtube-miniminterclips", "MiniminterClips"),
    ("UCo8bcnLyZH8tBIH9V1mLgqQ", "youtube-theodd1sout", "theodd1sout"),
    ("UCN-qGJtXJCiG0mMXR2fga6A", "youtube-jaidenanimations", "jaidenanimations"),
    ("UCZ1owRB7n8MyjK_cuk4zR6Q", "youtube-markiplier2", "PowerGlitch"),
    ("UCyUmevTef0H-pFaspmfTb3Q", "youtube-rtgame", "RTGame"),
    ("UCX1FhNnn_82e3sPdCkssy7g", "youtube-callmekevin", "Kevo"),
    ("UCpFHkjOa7ia6bH5_6cDsDXg", "youtube-gameranxtv", "Complex News"),
    ("UCpqXJOEqGS-TCnazcHCo0rA", "youtube-theradbrad", "theRadBrad"),
    ("UCMUyG01MXNeiTykIlvWwIRQ", "youtube-jacksfilms", "jacksfilms"),
    ("UCYucn3aPwdQJ7X6yn7-VWbQ", "youtube-vanossgaming", "vanossgaming"),
    ("UCTr1fTlg3nqxZ4m2Rdy58Hg", "youtube-h2odelirious", "Delirious Let's Play"),
    ("UCoUddkWzlmw1cExDMphmFkg", "youtube-coryxkenshin", "POiiSED"),
    ("UCfBpv6ahDMg7kEClQuMpzzw", "youtube-thegabbieshow", "TheGabbieShow"),
    ("UCJvR4zNAPRJoMDF3A912dBA", "youtube-emmachamberlain", "emmachamberlain"),
    ("UCef29bYGgUSoJjVkqhcAPkw", "youtube-daviddobrik", "DavidDobrik"),
    ("UCq8DICunczvLuJJq414110A", "youtube-zachking", "zachking"),
    ("UCxmpT2Gf0ui3NESdrUrlT-Q", "youtube-collinskey", "CollinsKey"),
    ("UCet_y01v87pE7MPGikjTQQw", "youtube-unspeakable", "unspeakable"),
    ("UC2hFZwNM71iOOCY3guLE7KQ", "youtube-sssniperwolf", "Little Lia"),
    ("UCuNgNRHKIiudXKPbTlvh0Pw", "youtube-aphmau", "Aphmau"),
    ("UCZ3AmknSJtbzXCeO5a4peoQ", "youtube-lazarbeam", "LazarLazar"),
    ("UCXrExb1m3VjR0m1_l9luxRQ", "youtube-lachlan", "PWR"),
    ("UCXq2nALoSbxLMehAvYTxt_A", "youtube-gamegrumps", "The Grumps"),
    ("UCxLIJccyaRQDeyu6RzUsPuw", "youtube-jacksucksatlife", "JackSucksAtStuff"),
    ("UCHpGOTBGfltnrLqxfJn6zog", "youtube-mrballen", "MrBallen"),
    ("UCihko5ga4v76RMM7ppF_XpA", "youtube-nightmind", "nightmind"),
    ("UC9RM-iSvTu1uPJb8X5yp3EQ", "youtube-halfasinteresting", "Wendover Productions"),
    ("UCpSUQewzOXg1F0zLmieKCqQ", "youtube-legaleagle", "LegalEagle"),
    ("UCmGSJVG3mCRXVOP4yZrU1Dw", "youtube-johnnyharris", "Search Party"),
    ("UC415bOPUcGSamy543abLmRA", "youtube-cleoabram", "cleoabram"),
    ("UCIBGTfBKee0lM8sJp4TOgUg", "youtube-morningbrew", "morningbrew"),
    ("UCGkpFfEMF0eMJlh9xXj2lMw", "youtube-coldfusion", "coldfusion"),
    ("UCaF_EnJKDAdFsToUhkLfFxw", "youtube-vsauce2", "Mind Blow"),
    ("UCRijo3ddMTht_IHyNSNXpNQ", "youtube-dudeperfectplus", "DudePerfectPlus"),
    ("UCli0KmmXMDjcgqvsheHfv-Q", "youtube-bbcsport", "BBC Football"),
    ("UCNAf1k0yIjyGu3k9BwAg3lg", "youtube-skysports", "SkySports"),
    ("UCTEXNK6sA1ryaHfXW9Q44Fg", "youtube-olympicchannel", "Olympiciha"),
    ("UCXnFh8S94wQCPw-p6j6bX9A", "youtube-bcci", "དK-SツSho-rtsཌ"),
    ("UCt2JXOLNxqry7B_4rRZME3Q", "youtube-icc", "ICC"),
    ("UC_WKb6N9iTGc77hxwXLDrbA", "youtube-sonysportsnetwork", "SonySportsNetwork"),
    ("UC2iihojySb58j_Q4zL7VI5w", "youtube-starsportsindia", "StarSportsIndia"),
    ("UCgZgm6v8ENPzFTgzLjgipRQ", "youtube-nbatv", "NBATV"),
    ("UCO9a_ryN_l7DIDS-VIt-zmw", "youtube-wnba", "WNBA"),
    ("UCSZbXT5TLLW_i-5W8FZpFsg", "youtube-mls", "Major League Soccer"),
    ("UCWV3obpZVGgJ3j9FVhEjF2Q", "youtube-realmadrid", "realmadrid"),
    ("UC14UlmYlSNiQCBe9Eookf_A", "youtube-fcbarcelona", "FCBarcelona"),
    ("UCpryVRk_VDudG8SHXgWcG0w", "youtube-arsenal", "Arsenal"),
    ("UCkzCjdRMrW2vXLx8mvPVLdQ", "youtube-mancity", "ManCity"),
    ("UCt9a_qP9CqHCNwilf-iULag", "youtube-psg", "psg"),
    ("UCLzKhsxrExAC6yAdtZ-BOWw", "youtube-juventus", "juventus"),
    ("UCle_9ogeckix384eRvTbVog", "youtube-fcbayern", "FCBayern"),
    ("UCeYc_OjHs3QNxIjti2whKzg", "youtube-warriors", "warriors"),
    ("UCC0BPKJxAyxjQoRTYbpW0FQ", "youtube-dallascowboys", "DallasCowboys"),
    ("UCQIyqMWCdx1GBvbw_Yi6lEA", "youtube-redbullracing", "redbullracing"),
    ("UClj0L8WZrVydk5xKOscI6-A", "youtube-mercedesamgf1", "Mercedes-Benz"),
    ("UCeQf8mZkzUswAL42uQs84iA", "youtube-motogp", "WorldSBK"),
    ("UCPrONRG9hO1f-OrxW-WH-xg", "youtube-bellatormma", "PFL MMA"),
    ("UCiormkBf3jm6mfb7k0yPbKA", "youtube-onechampionship", "onechampionship"),
    ("UCEVVENPnHv-kcp2PqQuJvHg", "youtube-boxing", "Seconds Out"),
    ("UCQpbsCYqUl-KfJL_X_TDrHg", "youtube-daznboxing", "DAZN Combat"),
    ("UC7LReVje9aPB4B6XAsXX8WQ", "youtube-matchroomboxing", "MatchroomBoxing"),
    ("UCBFuLjL_YMmgDQQ6viFtVtA", "youtube-skysportsnba", "SkySportsNBA"),
    ("UC5qUhMoqke0mnJtgVoEn0aw", "youtube-houseofhighlights", "Creator League"),
    ("UCO7BZhCe-EJxXIOU_O53n9g", "youtube-bleacherreport", "B/R Cartoons"),
    ("UCvZpZard_5r1x2gq7a2ByEA", "youtube-avocadocouple", "Avocado Family"),
    ("UCpmMQ8eFlmm4ZFJ852YRmQQ", "youtube-lalalifegames", "LaLaLifeGames"),
    ("UCrXwSLLq3YAYzalYoFbqNVw", "youtube-multido", "JuSt sMilE🙃"),
    ("UCije75lmV_7fVP7m4dJ7ZoQ", "youtube-sisvsbro", "GamerGirl"),
    ("UCCMeCQ4wtdwQuoH7TNThL1A", "youtube-alanchikinchow", "AU"),
    ("UCP9MW9ATjUwwulqEYTbp-Mw", "youtube-vladandniki", "VladandNiki"),
    (
        "UCxG6Tbopv4XcHfem65bgFeg",
        "youtube-supersimplesongs",
        "Super Simple Play with Caitie!",
    ),
    ("UCKAqou7V9FAWXpZd9xtOg3Q", "youtube-littlebabybum", "LittleBabyBum"),
    (
        "UC2qeJDvFWrnbHKHIpTbx6lA",
        "youtube-babyshark",
        "Kikipuppup - Nursery Rhymes with Cats & Dogs",
    ),
    ("UC5PYHgAzJ1wLEidB58SK6Xw", "youtube-blippi", "blippi"),
    ("UCGie8GMlUo3kBKIopdvumVQ", "youtube-netflix", "netflix"),
    ("UCyouSlyNTfwX_pnGvlfIL3Q", "youtube-primevideo", "Prime Movies"),
    ("UCx-KWLTKlB83hDI6UKECtJQ", "youtube-hbo", "HBO"),
    ("UC_5niPa-d35gg88HaS7RrIw", "youtube-disneyplus", "DisneyPlus"),
    ("UCxwitsUVNzwS5XBSC5UQV8Q", "youtube-marvel", "MARVEL"),
    ("UCZGYJFUizSax-yElQaFDp5Q", "youtube-starwars", "StarWars"),
    ("UCq7OHvWO6Z3u-LztFdrcU-g", "youtube-universalpictures", "Illumination"),
    ("UCP8AC-LXl5Jmp64IRIsdacg", "youtube-sonypictures", "Spider-Man"),
    ("UCuPivVjnfNo4mb3Oog_frZg", "youtube-a24", "A24"),
    (
        "UCE0Wkd9Jcn2-TNo5G8bLQrA",
        "youtube-rottentomatoestrailers",
        "RottenTomatoesTRAILERS",
    ),
    ("UCQMbqH7xJu5aTAPQ9y_U7WQ", "youtube-screenjunkies", "Fandom Entertainment"),
    ("UCYUQQgogVeQY8cMQamhHJcg", "youtube-cinemasins", "CinemaSins"),
    (
        "UCXDIl5ElYimqmasGFGmp7Eg",
        "youtube-lessonsfromthescreenplay",
        "LessonsfromtheScreenplay",
    ),
    ("UCjFqcJQXGZ6T6sxyFB-5i6A", "youtube-everyframeapainting", "everyframeapainting"),
    ("UCMAwBUlaxyqZY-2hVac8qgg", "youtube-patrickhwillems", "Patrick Willems Presents"),
    ("UCZ04pLI44c0PWRzubEV6ogA", "youtube-ralphthemoviemaker", "RalphTheMovieMaker"),
    ("UCrTNhL_yO3tPTdQ5XgmmWjA", "youtube-redlettermedia", "redlettermedia"),
    ("UCG_nvdTLdijiAAuPKxtvBjA", "youtube-filmento", "Filmento"),
    ("UCDylnpLJWDj2gKWujjwap9w", "youtube-studiobinder", "StudioBinder"),
    ("UCNvsIonJdJ5E4EXMa65VYpA", "youtube-contrapoints", "ContraPoints"),
    ("UCIPqOTYW439-5hUz6r3U1fA", "youtube-hbomberguy", "H.BurgerGuy"),
    ("UCfGA2WK6Rw-K1E_mn_gyW2g", "youtube-jacobgeller", "Something Rotten Podcast"),
    ("UCX1xppLvuj03ubLio8jslyA", "youtube-hikakintv", "HikakinGames"),
    ("UC9x4XNrxWVcl1Kvf2vlt6QQ", "youtube-hajimesyacho", "5億円ハウスの管理人"),
    (
        "UCOHybb6uSmbo3W0zTP4clcQ",
        "youtube-sushiramen",
        "ゲーム実況者ハルナ艦長 【Haruna Games】",
    ),
    ("UCo-f3WS0648Hg8Jqxx_ui-A", "youtube-pdrsan", "PDRsan"),
    ("UCQSN5wPCAaQt-jkSI5Ye7ag", "youtube-youtubejapan", "24時間健康情報"),
    ("UChQBrFzXf85v3qHCCk80oiA", "youtube-avex", "avex"),
    ("UC6KEU5-KSTszEOOnAl8ZwPQ", "youtube-kingrecords", "kingrecords"),
    ("UCBsbrudhKRrT9zs8iNOEjjw", "youtube-playstation", "Marathon"),
    ("UCydtMNspoPAlqBjFSGnigSw", "youtube-xbox", "Forza"),
    ("UCUzl0dAdU3IUGrChjqbMuqQ", "youtube-ignjapan", "IGNJapan"),
    (
        "UCq8ZAAsI89IoJ-fn1gYpO3g",
        "youtube-kurzgesagtde",
        "Nightshift – Kurzgesagt After Dark",
    ),
    ("UCFlqsKkyRi4nptSrdbkwdSA", "youtube-mrwissen2go", "aWish"),
    ("UCTXeJ33DzXI2veQpKfrvaYw", "youtube-julienbam", "JulienBam"),
    ("UCHfdTAyg5t4mb1G-3rJ6QsQ", "youtube-bibisbeautypalace", "BibisBeautyPalace"),
    ("UCZH94s66wDOTspVoKI7EYpg", "youtube-gronkh", "Gronkh"),
    ("UC3wla9xMoxDu7MIZImad1kQ", "youtube-pietsmiet", "PietSmiet"),
    ("UCu4F0fRi8FCSUbfjyQd8LXw", "youtube-concrafthd", "breadmanbry"),
    ("UCC9h3H-sGrvqd2otknZntsQ", "youtube-freekickerz", "freekickerz"),
    ("UCi7MkdJLwvV99438YeUhZeg", "youtube-cyprien", "Cyprien"),
    ("UCv1b9jffj3tEpdSc020-sGA", "youtube-mcfly", "Mcfly"),
    ("UCY-_QmcW09PHAImgVnKxU2g", "youtube-squeezie", "SQUEEZIE"),
    ("UCo6Z9cEI8Hf3nyrLUfDITtA", "youtube-inoxtag", "inoxtag"),
    ("UC8rNKrqBxJqL9izOOMxBJtw", "youtube-willyrex", "willyrex"),
    ("UC4LHNX8d8RqnDX0OezgmCTg", "youtube-vegetta777", "TheWillyrex"),
    ("UCEhV7Kms52H2HrdwthU2QmA", "youtube-djmariio", "DjMaRiiO"),
    ("UCRtkuS3Wz0hYgfJjpvEEP4Q", "youtube-lyna", "Lyna"),
    ("UCXazgXDIYyWH-yXLAkcrFxw", "youtube-elrubius", "elrubius"),
    ("UCcPI9kEPhyUDLBHGOhKqxOw", "youtube-aevytv", "Breakdown"),
    ("UChIZGfcnjHI0DG4nweWEduw", "youtube-techsource", "TechSource"),
    ("UCL3qzii9efb3Tbch2lG4Ocg", "youtube-jarrodstech", "Jarrod's Laptops"),
    ("UCDKLZBNM9XZ7pHPZF9D8xDQ", "youtube-hardwareunboxed", "Monitors Unboxed"),
    ("UCovpbOTYpkZnv1MXgCdkD0w", "youtube-optimumtech", "optimum plays"),
    ("UCy53VTYXp9w_6Svuz1afCgw", "youtube-jayztwocents", "JayzTwoCars"),
    ("UClb90NQQcskPUGDIXsQEz5Q", "youtube-developedbyed", "developedbyed"),
    ("UCvGwM5woTl13I-qThI4YMCg", "youtube-joshtriedcoding", "joshtriedcoding"),
    ("UCwE6vJXm1I3XmMA6g92HXxw", "youtube-thecherno", "More Cherno"),
    ("UC77N7im6bfUPvR3PkRKaVGQ", "youtube-javidx9", "javidx9"),
    ("UCtxCXg-UvSnTKPOzLH4wJaQ", "youtube-codingtech", "codingtech"),
    (
        "UCV_6HOhwxYLXAGd-JOqKPoQ",
        "youtube-microsoftdeveloper",
        "Microsoft 365 Developer",
    ),
    ("UC_x5XG1OV2P6uZZ5FSM9Ttw", "youtube-googledevelopers", "Google for Developers"),
    ("UCd6MoB9NC6uYN2grvUNT-Zg", "youtube-awsdevelopers", "Amazon Web Services"),
    ("UC76AVf2JkrwjxNKMuPpscHQ", "youtube-dockerinc", "DockerInc"),
    ("UCaiL2GDNpLYH6Wokkk1VNcg", "youtube-mcoding", "mCoding"),
    ("UCuudpdbKmQWq2PPzYgVCWlA", "youtube-indently", "Indently"),
    ("UCCezIgC97PvUuR4_gbFUs5g", "youtube-dataschool", "Corey Schafer"),
    ("UCtYLUTtgS3k1Fg4y5tAhLbw", "youtube-statquest", "StatQuest"),
    ("UC_SvYP0k05UKiJ_2ndB02IA", "youtube-blackpenredpen", "blackpenredpen"),
    ("UCC6Wl-xnWVS9FP0k-Hj5aiw", "youtube-michaelpennmath", "MathMajor"),
    ("UCH74Hc_7WYVzx1GXhLEH6Eg", "youtube-mathologer", "mathologer"),
    ("UCSju5G2aFaWMqn-_0YBtq5A", "youtube-standupmaths", "standupmaths"),
    ("UCRfo-DAifrP3lzcxUHtGm_A", "youtube-tomrocksmaths", "tomrocksmaths"),
    ("UCHEnZhUKjZSLYs3jJ0raKZA", "youtube-anotherroof", "AnotherRoof"),
    ("UCHnj59g7jezwTy5GeL8EA_g", "youtube-mindyourdecisions", "MindYourDecisions"),
    ("UCzBjutX2PmitNF4avysL-vg", "youtube-aleph0", "Aleph0"),
    ("UCIEv3lZ_tNXHzL3ox-_uUGQ", "youtube-gordonramsay", "gordonramsay"),
    ("UC1rIOwTqDuWkFj87HZYRFOg", "youtube-nytcooking", "nytcooking"),
    ("UC4tAgeVdaNB5vD_mBoxg50w", "youtube-foodwishes", "Allrecipes"),
    ("UCYjk_zY-iYR8YNfJmuzd70A", "youtube-epicmealtime", "EpicMealTime"),
    ("UCfyehHM_eo4g5JUyWmms2LA", "youtube-sortedfood", "SortedFood"),
    ("UCICdNqyJqyHB3_uDVtmFhPA", "youtube-ethanchlebowski", "EthanChlebowski"),
    ("UCOcphUKAnUaair1uZ7SlqiA", "youtube-internetshaquille", "Extranet Shaquille"),
    ("UC9_p50tH3WmMslWRWKnM7dQ", "youtube-aragusea", "Adam Ragusea"),
    ("UCVVAnxQ2YMC_qlc7QfPA2YQ", "youtube-almazankitchen", "AlmazanKitchen"),
    ("UCfE5Cz44GlZVyoaYTHJbuZw", "youtube-guga", "guga"),
    ("UC2HNqPgeKtVr2gZmLeeIk3g", "youtube-nickdigiovanni", "Nick's Kitchen"),
    ("UC_pT_Iz6XjuM-eMTlXghdfw", "youtube-maxthemeatguy", "maxthemeatguy"),
    ("UC4avs5jYd_FvzQ8f0XYziqw", "youtube-bingingwithbabish", "Beyond Babish"),
    ("UCbKLRsBRSYDQwq8yd8C3ZYA", "youtube-charismaoncommand", "Dropping In Podcast"),
    ("UCBIt1VN5j37PVM8LLSuTTlw", "youtube-improvementpill", "ImprovementPill"),
    ("UCd_WBvzBg1UbHE8j8MIL5Ng", "youtube-thomasfrank", "ThomasFrank"),
    ("UCqRnyszSh6EslfZA-BJfftw", "youtube-betterideas", "Joey Schweitzer"),
    ("UCrdWRLq10OHuy7HmSckV3Vg", "youtube-nathanieldrew", "NathanielDrew"),
    (
        "UCNRL-_4emfF_ZamFOWCF2rg",
        "youtube-thefinancialdiet",
        "The Financial Confessions Highlights",
    ),
    ("UChxc_Lg9sh3aYBjVS9h_SHA", "youtube-twocents", "TwoCents"),
    ("UCVWDbXqQ8cupuVpotWNt2eg", "youtube-biggerpockets", "On The Market"),
    ("UCPk6nJE8pBZPLCW2DAvaZOA", "youtube-meetkevin", "MeetKevin"),
    ("UCRO-azXc5JrPHnxX2r6-eNQ", "youtube-minoritymindset", "MinorityMindset"),
    ("UCO3tlaeZ6Z0ZN5frMZI3-uQ", "youtube-nateobrien", "NateOBrien"),
    ("UCbta0n8i6Rljh0obO7HzG9A", "youtube-josephcarlsonshow", "JosephCarlsonShow"),
    ("UCJm2RBjxfvdTdtJcYtFx2Xw", "youtube-everythingmoney", "everythingmoney"),
    ("UCAeAB8ABXGoGMbXuYPmiu2A", "youtube-theswedishinvestor", "TheSwedishInvestor"),
    (
        "UCCmJVw9xQfYuuAAwZGedKRg",
        "youtube-financialeducation",
        "Jeremy Lefebvre - 1000xstocks",
    ),
    ("UCo92D-IJgfR-ZUe1_zeDFDg", "youtube-charliechang", "CharlieChang"),
    ("UCNIoLiHvnuKTKoJuLQUS--A", "youtube-marktilbury", "MarkTilbury"),
    ("UCTHEFQsEHn6gfM44zYRwFxQ", "youtube-damonimani", "DamonImani"),
    ("UCEAZeUIeJs0IjQiqTCdVSIg", "youtube-yahoofinance", "YahooFinance"),
    ("UCL_v4tC26PvOFytV1_eEVSg", "youtube-whiteboardfinance", "WhiteboardFinance"),
    ("UC5CkZdoQwz_3VxwnxXSEISA", "youtube-tommybryson", "TommyBryson"),
    ("UCAqAp1uh_5-tmEimhSqtoyw", "youtube-calebhammer", "CalebHammer"),
    ("UC7ZddA__ewP3AtDefjl_tWg", "youtube-ramitsethi", "I Will Teach You To Be Rich"),
    ("UCBRpqrzuuqE8TZcWw75JSdw", "youtube-thecompoundnews", "TheCompoundNews"),
    ("UCzQUP1qoWDoEbmsQxvdjxgQ", "youtube-joerogan", "PowerfulJRE"),
    ("UCSHZKyawb77ixDdsGog4iWA", "youtube-lexclips", "Lex Fridman"),
    ("UCIaH-gZIVC432YRjNVvnyCA", "youtube-chriswillx", "Chris Williamson"),
    ("UCLtREJY21xRfCuEKvdki1Kw", "youtube-h3podcast", "H3Podcast"),
    ("UCvYrhzKs1c8LajTP687ifEA", "youtube-flagrantpodcast", "FlagrantPodcast"),
    ("UC8m47evCGVLqbX8wGyx7_7g", "youtube-thefighterandthekid", "Drive Fast All Gas"),
    ("UCTLh-XHAAsXGedkx8u7DOWw", "youtube-distractibleclips", "DistractibleClips"),
    ("UCyFqFYfTW2VoIQKylJ04Rtw", "youtube-acquiredfm", "acquiredfm"),
    ("UC6t1O76G0jYXOAoYCm153dA", "youtube-lennyspodcast", "lennyspodcast"),
    ("UC5fdyC4LxyyYv8Am6nDrkmg", "youtube-foundmyfitness", "FoundMyFitness"),
    ("UC8kGsMa0LygSX9nkBcBH1Sg", "youtube-peterattiamd", "PeterAttiaMD"),
    ("UChVak8_IyuqcErdf_jQUOHA", "youtube-mindpumpshow", "Mind Pump TV"),
    ("UCm-S1o46FtTx-ATgJoOv74A", "youtube-thedailystoic", "TheDailyStoic"),
    ("UC2PA-AKmVpU6NKCGtZq_rKQ", "youtube-philosophytube", "philosophytube"),
    ("UC1KmNKYC1l0stjctkGswl6g", "youtube-academyofideas", "After Skool"),
    ("UC-tLyAaPbRZiYrOJxAGB7dQ", "youtube-pursuitofwonder", "pursuitofwonder"),
    ("UCcoO-8J0EYQHGPFQqwmAzVQ", "youtube-exurb1a", "exurb2a"),
    ("UC7IcJI8PUf5Z3zKxnZvTBog", "youtube-theschooloflifetv", "theschooloflifetv"),
    ("UCswF-Mg6JuPBdHHzoK9ftDQ", "youtube-bigthink", "bigthink"),
    ("UCP5tjEmvPItGyLhmjdwP7Ww", "youtube-reallifelore", "reallifelore"),
    ("UCtYKe7-XbaDjpUwcU5x0bLg", "youtube-neoexplains", "neoexplains"),
    ("UCgNg3vwj3xt7QOrcIDaHdFg", "youtube-polymatter", "PolyMatter"),
    ("UCVWX3F3DrTvDKa0LRilQoQQ", "youtube-economicsexplained", "Context Matters"),
    ("UCKfak8fBm_Lhy4eX9UKxEpA", "youtube-theinfographicsshow", "The Military Show"),
    ("UCZiQAZiC1W9bUUMVOrMckdg", "youtube-hai", "Mh_sezar"),
    ("UCTWKe1zATFV6d0o6oLS9sgw", "youtube-wendoverproductions", "Extremities"),
    ("UC1ZBQ-F-yktYD4m5AzM6pww", "youtube-mustardchannel", "MustardChannel"),
    ("UClhGRUBCbui0IKCAe-ezG3A", "youtube-notjustbikes", "The Urbanist Agenda Podcast"),
    ("UCfgtNfWCtsLKutY-BHzIb9Q", "youtube-citynerd", "CityNerd"),
    ("UClfEht64_NrzHf8Y0slKEjw", "youtube-alternatehistoryhub", "AlternateHistoryHub"),
    ("UC22BdTgxefuvUivrjesETjg", "youtube-historymatters", "historymatters"),
    ("UCCGvq-qmjFmmMD4e-PLQqGg", "youtube-kingsandgenerals", "The Cold War"),
    ("UCdgB20VoUI3Gz3Qe-w4XOrg", "youtube-knowledgia", "Knowledgia"),
    ("UCHKRfxkMTqiiv4pF99qGKIw", "youtube-biographics", "Geographics"),
    ("UClnDI2sdehVm1zm_LmUHsjQ", "youtube-geographicstravel", "Biographics"),
    (
        "UCfnDU4kac3TGJV9qlpXun2g",
        "youtube-megaprojects9649",
        "Megaprojects in Italiano",
    ),
    ("UC0woBco6Dgcxt0h8SwyyOmw", "youtube-sideprojects", "Megaprojects"),
    ("UC-ynNaRCarJKgTzentD109Q", "youtube-warographics643", "HomeFronts"),
    ("UCPdc6bs3I8s6Y4QE_3g3MZw", "youtube-simplehistory", "simplehistory"),
    ("UCFFbwnve3yF62-tVXkTyHqg", "youtube-zeemusiccompany", "zeemusiccompany"),
    ("UCJrDMFOdv1I2k8n9oK_V21w", "youtube-tipsofficial", "TIPSOfficial"),
    ("UC3MLnJtqc_phABBriLRhtgQ", "youtube-sonymusicindiavevo", "SonyMusicIndiaVEVO"),
    ("UCyoXW-Dse7fURq30EWl_CUA", "youtube-goldminestelefilms", "GoldminesTelefilms"),
    ("UCBbtDbiqcdRP1rqFiEwhu1A", "youtube-wavemusic", "Paradise Music"),
    ("UCOsyDsO5tIt-VZ1iwjdQmew", "youtube-speedrecords", "SpeedRecords"),
    ("UCaayLD9i5x4MmIoVZxXSv_g", "youtube-tseriesbhaktisagar", "TseriesBhaktiSagar"),
    ("UCYPvAwZP8pZhSMW8qs7cVCw", "youtube-aajtak", "India Today"),
    ("UCRWFSbif-RFENbBrSiez1DA", "youtube-abpnews", "ABPNEWS"),
    ("UCttspZesZIDEwwpVIgoZtWQ", "youtube-indiatv", "IndiaTV"),
    ("UCIvaYmXn910QMdemBG3v1pQ", "youtube-zeenews", "ZeeNews"),
    ("UCPP3etACgdUWvizcES1dJ8Q", "youtube-news18india", "news18india"),
    ("UChIuMQsOdbrc4Evj_raoDZA", "youtube-republicworld", "Republic Defence"),
    ("UC6RJ7-PaXg6TIH2BzZfTV7w", "youtube-timesnow", "TimesNow"),
    ("UC0IWRLai-BAwci_e9MylNGw", "youtube-carryminati", "CarryisLive"),
    ("UCUxNHDxPFjuKMdMPAsYVJMQ", "youtube-bbkivines", "BBKiVines"),
    ("UCNTabXK2VCqj1dTQhq_jRsA", "youtube-amitbhadana", "AmitBhadana"),
    ("UCOjRVCxaNntzhUhwUF-xCFA", "youtube-round2hell", "Round2hell"),
    (
        "UChmCol08IsWTety5a3rMh6w",
        "youtube-ashishchanchlanivines",
        "AshishChanchlaniVines",
    ),
    ("UCXsXitjiT_8qPgNEFGPVfBA", "youtube-technicalguruji", "Gaurav Chaudhary"),
    ("UCn8Fiasqd-6G3A6AS322mZA", "youtube-flyingbeast320", "FitMuscle TV"),
    (
        "UCl_vAxZpvbO-PFXdDu7EdHw",
        "youtube-technogamerzofficial",
        "TechnoGamerzOfficial",
    ),
    ("UCGpSJk0zi-wDrCIzjrxrk0w", "youtube-totalgaming093", "AJAY VERSE"),
    ("UCFwKgzKe-EdTz83r6wzhmOw", "youtube-triggeredinsaan", "Live Insaan"),
    ("UCcjIvuxmWlS5IEQ0JdPV4Ng", "youtube-elrubiusomg", "Rubius Z"),
    ("UCFR2oaNj02WnXkOgLH0iqOA", "youtube-auronplay", "AuronPlay"),
    ("UC52YgT6TITyBpck82V_N_8g", "youtube-elmariana", "elmariana"),
    ("UCwosQ1lgv4kez9V4xUbJWKQ", "youtube-fernanfloo", "Fernanfloo"),
    ("UCnmlCrWnJZ-YdDFcVKOnjhA", "youtube-thegrefg", "Ampeterby7"),
    ("UCxydCvDiNVYywwdj93c9j8Q", "youtube-juanguarnizo", "Dario Tapia"),
    ("UCECJDeK0MNapZbpaOzxrUPA", "youtube-luisitocomunica", "LuisitoComunica"),
    ("UCzoUWqjCbcfWFdOMvoep8FA", "youtube-kimberlyloaiza", "Juan De Dios Pantoja"),
    ("UCYiGq8XF7YQD00x7wAd62Zg", "youtube-holasoygerman", "JuegaGerman"),
    ("UCIzdh7oty8jCnXUj3eUj2WQ", "youtube-felipeneto", "felipeneto"),
    ("UCZMeVcAtZMZDtXPodW376sg", "youtube-authenticgames", "AuthenticGames"),
    ("UC7iyparkdas-4UTSL_gktQg", "youtube-rezendeevil", "rezendeevil"),
    ("UC9u6Fd9XhDJPXggSUvsiOgg", "youtube-enaldinho", "Elo Team"),
    ("UCEWHPFNilsT0IfQfutVzsag", "youtube-portadosfundos", "PortaDosFundos"),
    ("UCZ2HtmLHc33CczdI8PHs2NA", "youtube-kondzilla", "Pé Na Porta"),
    ("UC3IZKseVpdzPSBaWxBxundA", "youtube-hybelabels", "HYBELABELS"),
    ("UC9GtSLeksfK4yuJ_g1lgQbg", "youtube-smtown", "aespa"),
    ("UCjO4StI9jjPI9xSIIixsYdw", "youtube-1thek", "퍼스널 Personal"),
    ("UCaO6TYtlC8U5ttz62hTrZgg", "youtube-jypentertainment", "JYPEntertainment"),
    ("UCrDkAvwZum-UTjHmzDI2iIw", "youtube-officialpsy", "officialpsy"),
    ("UCzgxx_DM2Dcb9Y1spb9mUJA", "youtube-twice", "TWICE"),
    ("UC9rMiEjNaCSsebs31MRDCRA", "youtube-straykids", "StrayKids"),
    ("UCgX5gdpNdTnQDAAFCgUaFZw", "youtube-mrbeastinhindi", "MrBeastInHindi"),
    ("UC8Q1gJfcRy5HKweJJb35gyQ", "youtube-arabsgottalent", "MBC THE VOICE KIDS"),
    ("UCrj5BGAhtWxDfqbza9T9hqA", "youtube-alarabiya", "AlHadath الحدث"),
    ("UC6kwA_uLrl-a3EdkY_aDJ-w", "youtube-attahalilintar", "AHHA RECORDS"),
    ("UCCFiS17fEvt7UmAV6okAmfA", "youtube-ransentertainment", "POWERRANSGERS"),
    ("UCoIiiHof6BJ85PLuLkuxuhw", "youtube-windahbasudara", "windahbasudara"),
    ("UCaE0iH4KmJl_JoomVP02fsw", "youtube-deddycorbuzier", "deddycorbuzier"),
    ("UCfRNJiafEm1LBBGFTTq4cXw", "youtube-genhalilintar", "GenHalilintar"),
    ("UCneA4BuveCEgJql1m7lwFag", "youtube-kompastv", "kompastv"),
    ("UCER4rvDnRBPr_ncYW4UCZjg", "youtube-tvonenews", "tvOneNews"),
    ("UCXZuKhvf6ZdLpqHMuXSC0Fw", "youtube-trans7official", "TRANS7 Lifestyle"),
    ("UCpiEAWJPccKm2UXGcEVnDdQ", "youtube-pewdiepieindo", "PewDiePieIndo"),
    ("UCLCnaHLXHpHz1atQkyi7ZsQ", "youtube-schannelvn", "HÔM NAY ĂN GÌ"),
    ("UCkgdDBHO7zl3tWIjldQeK7g", "youtube-popskids", "POPS Anime"),
    ("UCtBu8Wb2BUoduUXJS9Uss7Q", "youtube-thaich8", "thaich8"),
    ("UC3ZkCd7XtUREnjjt3cyY_gg", "youtube-workpointofficial", "WorkpointOfficial"),
    ("UC_mceLIVkQun_Xcu1KBmfdw", "youtube-gmmtv", "GMMTV"),
    ("UClMWr36fdau7kJK5Z7m2-XA", "youtube-orkunisitmak", "Orkun v2"),
    ("UCAfkLSa-ujPKhniiKZ2bCHg", "youtube-wylsacom", "WylsaLive"),
    ("UCrFiA0hztL9e8zTi_qBuW4w", "youtube-eeoneguy", "EeOneGuy"),
    ("UCzBTlYfHYMwVEru4hmLM8hg", "youtube-manualdomundo", "manualdomundo"),
    ("UCH2VZQBLFTOp6I_qgnBJCuQ", "youtube-nostalgia", "nostalgia"),
    ("UCMj5O3IvbTbOx35bMRHGtzA", "youtube-canalnostalgia", "ANTENA 24"),
    ("UCn9Erjy00mpnWeLnRqhsA1g", "youtube-cienciatododia", "Ciência Todo Dia"),
    ("UCSTlOTcyUmzvhQi6F8lFi5w", "youtube-atilaiamarino", "AtilaIamarino"),
    ("UCvdwhh_fDyWccR42-rReZLw", "youtube-cnnbrasil", "CNNBrasil"),
    ("UC376n347Ob5Lwzq2WGzF1AA", "youtube-sbtnews", "SBTNews"),
    ("UCoa-D_VfMkFrCYodrOC9-mA", "youtube-bandjornalismo", "bandjornalismo"),
    ("UCIzAIM-zatIDHErC0Z23hbQ", "youtube-multishow", "multishow"),
    ("UCZiYbVptd3PVPf4f6eR6UaQ", "youtube-cazetv", "CazéTV"),
    ("UC4ncvgh5hFr5O83MH7-jRJg", "youtube-cortesdoflow", "Flow Podcast"),
    ("UCvK1hfLpKidYjoo4hlj4vFg", "youtube-maisvoceoficial", "maisvoceoficial"),
    ("UCRRZRRUhSicWsEs30BXMH7g", "youtube-aztecauno", "Jorge FR"),
    ("UCtA8L08bjbI9wD-pEFLLFPQ", "youtube-curiosamente", "curiosamente"),
    ("UC65IX-jCCdgZcpklAguFFJA", "youtube-cdeciencia", "CdeCiencia"),
    ("UC6lHx7hjQq0_SX0jWj2dwFg", "youtube-dateunvlog", "ikefuti"),
    (
        "UCjZYt-dPU_H_O-hMx_yd5Ug",
        "youtube-elrobotdeplaton",
        "El Robot de Platón Pregunta",
    ),
    ("UCbdSYaPD-lr1kW27UJuk8Pw", "youtube-quantumfracture", "QuantumFracture"),
    ("UCwJrDbRJBGvIdYrpBMNtCIg", "youtube-lospolinesios", "PlaticaPolinesia"),
    ("UCUqvWUXerEGX33z3wmOnPrw", "youtube-dalasreview", "Dalas SIN FILTROS"),
    ("UCbavroIISer3JbHzIkEgO1Q", "youtube-pewdiepiebr", "PewDiePieBR"),
    ("UCIlxpbeL-5zJ2MU4gAof8aA", "youtube-markangelcomedy", "Mark Angel TV"),
    ("UC-iaCAZbuFSAmiSEQKgrC7Q", "youtube-sydneytalker", "SydneyTalker"),
    ("UCG6orNVuXIICv9_ifH6msIA", "youtube-brodashaggi", "brodashaggi"),
    ("UCghHIU61bZVqFPvZpYGyetg", "youtube-craftfactory", "craftfactory"),
    ("UCqLKODDhJLmOGlLSYqFaVRA", "youtube-mediaset", "Mediaset"),
    ("UCMggu4tZ2N6SD4FebIbMDpA", "youtube-st3pny", "st3pny"),
    ("UC1jTVZboWRPpjGKAN921M5w", "youtube-cicciogamer89", "CiccioGamer89"),
    ("UCD-aXv7CMezGSTfxmKAD6Ag", "youtube-ipantellas", "iPantellas"),
    ("UCfGk2x9k0vE14OoMlifGLCg", "youtube-mecontrote", "MeControTe"),
    ("UCQgQZdC52kP5V1XI3o5ux4g", "youtube-geopop", "geopop"),
    ("UC-BRUJOtblqGrftY6oRcOZw", "youtube-blowek", "blowek"),
    ("UC2tu25e6qqQ9m0rwAu0Vf3g", "youtube-reziofficial", "ReziOfficial"),
    ("UCoLrcjPV5PbUrUyXq5mjc_A", "youtube-mlb", "MLB"),
    ("UCK3CHl-6e3hq4gQaz_TOyoQ", "youtube-nhl", "NHL"),
    ("UCyGa1YEx9ST66rYrJTGIKOw", "youtube-uefa", "uefa"),
    ("UCTv-XvfzLX3i4IGWAm4sbmA", "youtube-laliga", "LaLiga"),
    ("UCbcxFkd6B9xUU54InHv4Tig", "youtube-tennistv", "TennisTV"),
    ("UCZoQ6VBnQGF2T3hwevWLJUA", "youtube-pgatour", "Korn Ferry Tour"),
    ("UCPSc8x8cAdI6-dKk61I4tGA", "youtube-nascar", "NASCAR"),
    ("UC8VddvuHJzIj__Ud0rY2_ww", "youtube-redbull", "redbull"),
    ("UC-WMwOzgFdvvGVLB1EZ-n-w", "youtube-gopro", "Sam Pilgrim"),
    ("UC0QgHEWL6ikOGutuBPVhI2A", "youtube-dudeperfect2", "El You See Why"),
    ("UCFN4JkGP_bVhAdBsoV9xftA", "youtube-aew", "All Elite Wrestling"),
    ("UC5AQEUAwCh1sGDvkQtkDWUQ", "youtube-theovon", "TheoVon"),
    ("UC5PstSsGrRwj2o6asQpC4Rg", "youtube-flagrantclips", "flagrantclips"),
    ("UCE-gv6zO4Qo6AAZiLvuVN3w", "youtube-themmaguru", "theMMAGuru"),
    ("UC_kdjhHnkUbSImMrezjRyDQ", "youtube-olympics", "Olympics"),
    ("UCrVdmT0b9msRjf98EsL575Q", "youtube-worldrugby", "worldrugby"),
    ("UC6UL29enLNe4mqwTfAyeNuw", "youtube-bundesliga", "Bundesliga"),
    ("UCxfPjORdISQSn2fV8tcVmgA", "youtube-seriea", "SerieA"),
    ("UClvow1RFSyeh5CRwRB_m5sA", "youtube-brfootball", "brfootball"),
    ("UCFIdU1RkuRd26YDA7lerfEQ", "youtube-copa90", "COPA90"),
    ("UC4SUUloEcrgjsxbmy_rQQXA", "youtube-442oons", "442oons"),
    ("UCqYaVuSy3gX-qqBKirfzJjw", "youtube-theathletic", "TheAthletic"),
    ("UCoBjkHP1sBfSDsvTNuSVDng", "youtube-goal", "goal"),
    ("UCYRE3PMYatMVXmqmulF0sgA", "youtube-sportbible", "LADbible Entertainment"),
    ("UCDtwmlSRVWsZsQSJjLS78VA", "youtube-overtime", "Overtime"),
    ("UCqZQlzSHbVJrwrn5XvzrzcA", "youtube-nbcsports", "NBCSports"),
    ("UCvQrivswRDGK0lZ_AcUHp8g", "youtube-foxsports", "NFL on FOX"),
    ("UCX_tjI6Q_4JD1E3234CwemA", "youtube-cbssportsgolazo", "CBS Sports W Golazo"),
    ("UCJUCcJUeh0Cz2xyKwkw5Q1w", "youtube-beinsports", "beINSPORTS"),
    ("UCSZ21xyG8w_33KriMM69IxQ", "youtube-daznfootball", "DAZNFootball"),
    ("UCVIoIHQIuIL5_ec2W3C9BAw", "youtube-talksport", "TalkSport"),
    ("UCujuVKmt_utAQZJghxlRMIQ", "youtube-espncricinfo", "ESPNCricinfo"),
    ("UCmqfX0S3x0I3uwLkPdpX03w", "youtube-starsports", "StarSports"),
    ("UC9-y-6csu5WGm29I7JiwpnA", "youtube-computerphile", "Computerphile"),
    ("UCeeFfhMcJa1kjtfZAGskOCA", "youtube-techlinked", "TechLinked"),
]


# "Streamed 3 hours ago" / "2 weeks ago" → seconds before now.
_AGO_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,
    "year": 31536000,
}
_AGO_RE = re.compile(r"(\d+)\s+(second|minute|hour|day|week|month|year)")


def _published_ms(text: str | None, now_ms: int) -> int | None:
    if not text:
        return None
    match = _AGO_RE.search(text)
    if match is None:
        return None
    return now_ms - int(match.group(1)) * _AGO_SECONDS[match.group(2)] * 1000


def _initial_data(page: str) -> dict[str, Any]:
    marker = "var ytInitialData = "
    start = page.find(marker)
    if start < 0:
        raise NewsFetchError("no ytInitialData on channel page")
    start += len(marker)
    end = page.find(";</script>", start)
    if end < 0:
        raise NewsFetchError("unterminated ytInitialData on channel page")
    return json.loads(page[start:end])


def _uploads(data: dict[str, Any], now_ms: int) -> list[NewsItem]:
    try:
        tabs = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
    except (KeyError, TypeError) as exc:
        # Consent/captcha interstitials carry ytInitialData with none of the
        # channel structure - a fetch failure, not a crash.
        raise NewsFetchError("channel page has no tab structure") from exc
    grid = None
    for tab in tabs:
        content = tab.get("tabRenderer", {}).get("content", {})
        if "richGridRenderer" in content:
            grid = content["richGridRenderer"]
            break
    if grid is None:
        raise NewsFetchError("no uploads grid on channel page")
    items: list[NewsItem] = []
    for cell in grid.get("contents", []):
        content = cell.get("richItemRenderer", {}).get("content", {})
        video_id: str | None = None
        title: str | None = None
        published: str | None = None
        # YouTube is mid-migration between two grid components; channels
        # serve either, so both are read.
        if "lockupViewModel" in content:
            lockup = content["lockupViewModel"]
            video_id = lockup.get("contentId")
            meta = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
            title = meta.get("title", {}).get("content")
            rows = (
                meta.get("metadata", {})
                .get("contentMetadataViewModel", {})
                .get("metadataRows", [])
            )
            for row in rows:
                for part in row.get("metadataParts", []):
                    text = part.get("text", {}).get("content", "")
                    if _AGO_RE.search(text):
                        published = text
                        break
                if published is not None:
                    break
        elif "videoRenderer" in content:
            video = content["videoRenderer"]
            video_id = video.get("videoId")
            runs = video.get("title", {}).get("runs", [])
            title = runs[0]["text"] if runs else None
            published = video.get("publishedTimeText", {}).get("simpleText")
        if not video_id or not title:
            continue
        url = f"https://www.youtube.com/watch?v={video_id}"
        items.append(
            NewsItem(
                id=url,
                title=title,
                url=url,
                pub_date=_published_ms(published, now_ms),
            )
        )
    return items


def _make_getter(channel_id: str, source_id: str) -> None:
    _url = f"https://www.youtube.com/channel/{channel_id}/videos"

    async def _getter() -> list[NewsItem]:
        # SOCS skips the EU consent interstitial (same cookie gnews uses);
        # the client's Accept-Language keeps publishedTimeText in English so
        # the relative-time parse holds.
        page = await fetch_text(_url, headers={"Cookie": "SOCS=CAI"})
        # The embedded JSON runs to ~1 MB - parse it off the event loop.
        data = await asyncio.to_thread(_initial_data, page)
        items = _uploads(data, int(time.time() * 1000))
        if not items:
            raise NewsFetchError(f"Cannot fetch YouTube uploads for {source_id}")
        return items[:30]

    register(source_id, _getter)


for _cid, _sid, _disp in _CHANNELS:
    _make_getter(_cid, _sid)

# Verified per-category channel batch (news.youtube_extra) - register any that
# aren't already in the base list above.

_existing = {sid for _c, sid, _d in _CHANNELS}
for _cid, _sid, _name, _col in YOUTUBE_EXTRA:
    if _sid not in _existing:
        _make_getter(_cid, _sid)

# Public source_id -> display, consumed by metadata generation.
YOUTUBE_CHANNELS: dict[str, str] = {sid: disp for _c, sid, disp in _CHANNELS}
