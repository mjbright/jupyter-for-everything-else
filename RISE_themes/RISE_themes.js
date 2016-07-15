
var alertChange = function() {
    var selectedIndex = d3.event.target.selectedIndex;
    var selectedDOMElement = d3.event.target.children[selectedIndex];
    var selection = d3.select(selectedDOMElement);
    loadcss(themes[ selection.text()]);   
};

var themes = {
    "mysky": "RISE_themes/mysky.css",
    "beige": "RISE_themes/beige.css",
    "blood": "RISE_themes/blood.css",
    "default": "RISE_themes/default.css",
    "moon": "RISE_themes/moon.css",
    "mybloodredsky": "RISE_themes/mybloodredsky.css",
    "mysky.pyconfr2015": "RISE_themes/mysky.pyconfr2015.css",
    "night": "RISE_themes/night.css",         
    "serif": "RISE_themes/serif.css",         
    "simple": "RISE_themes/simple.css",       
    "sky": "RISE_themes/sky.css",             
    "solarized": "RISE_themes/solarized.css"
};

function loadcss(filename) {
    var fileref=document.createElement("link");
        fileref.setAttribute("rel", "stylesheet");
        fileref.setAttribute("type", "text/css");
        fileref.setAttribute("href", filename);      
        document.getElementsByTagName("head")[0].appendChild(fileref);
};

var theme_opts = Object.keys(themes);

//add event listener to the 'theme-list' menu:
d3.select("#theme-list").on("change", alertChange).selectAll('option').data(theme_opts).enter().append("option").text(function(d){return d;});
d3.select("#theme-list0").on("change", alertChange).selectAll('option').data(theme_opts).enter().append("option").text(function(d){return d;});

loadcss("mysky");

