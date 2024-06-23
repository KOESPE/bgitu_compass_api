var i = 0;
var images = [];
var time = 5000; // время смены изображений

images[0] = "/static/image2.png";
images[1] = "/static/image1.png";

function changeImg(){
    var img = document.getElementById("app-preview");
    img.classList.add("hide");

    // После анимации скрытия, меняем изображение и показываем его
    setTimeout(function() {
        img.src = images[i];

        if(i < images.length - 1){
            i++;
        } else {
            i = 0;
        }

        img.classList.remove("hide");
    }, 1000); // время анимации скрытия

    // Устанавливаем следующий вызов функции смены изображения
    setTimeout(changeImg, time);
}

window.onload = function() {
    // Устанавливаем начальную задержку перед первой сменой изображения
    setTimeout(changeImg, 3000);
};