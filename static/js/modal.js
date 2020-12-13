
var modal = document.getElementById("img-popup");
var modalImg = document.getElementById("modal-img");
function zoomImg(id){
    var imgToDisplay = document.getElementById(id);
    modal.style.display = "flex";
    modalImg.src = imgToDisplay.src;
}
modal.onclick = function() { 
    modal.style.display = "none";
}