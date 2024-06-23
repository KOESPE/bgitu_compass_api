const selectButton = document.querySelectorAll('.js-st-select > .select-button');
const options = document.querySelectorAll('.js-st-select .select-list__option');

let index = 1;

// const Select = {
//     parent      : '.js-select',
//     selectButton: this.parent.concat('-button'),
//     selectList  : this.parent.concat('-list'),
//     selectOption: this.selectList.concat('-option'),
//     selectImg   : this.selectOption.concat('-img'),
//     selectText  : this.selectOption.concat('-text'),
//
//     expand: function ($button) {
//         $button.addEventListener('click', () => {
//             $button.querySelector(this.selectList)
//                 .classList
//                 .toggle('toggle');
//         })
//     }
// };


selectButton.forEach(a => {
    a.addEventListener('click', b => {
        const next = b.currentTarget.nextElementSibling;
        b.currentTarget.classList.toggle('toggle');
        next.classList.toggle('toggle');
        next.style.zIndex = index++;
    })
});

options.forEach(a => {
    a.addEventListener('click', b => {
        b.target.parentElement.classList.remove('toggle');

        const parent = b.target.closest('.select').children[0];
        parent.setAttribute('data-name', b.target.getAttribute('data-name'));
        // parent.innerText = b.target.innerText;
    })
});