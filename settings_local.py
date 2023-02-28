settings_local = {
    "templates_local": "./templates",  # Override templates
    "static_local": "./static",  # Change static folder
    "main_menu": [
        {
            "name": "home", 
            "title": "Hjem"
        },
        {
            "name": "about", 
            "title": "Om"
        },
        {
            "name": "login", 
            "title": "Log ind"
        }
    ],
    "pages": [
        {
            "name": "home", 
            "title": "Hjem", 
            "page": "pages/home.html", 
            "url": "/"
        },
        {
            "name": "about", 
            "title": "Om", 
            "page": "pages/about.html", 
            "url": "/about"
        }
    ]
}
