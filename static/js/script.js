document.addEventListener("DOMContentLoaded", function () {

    const menuToggle =
        document.getElementById("menuToggle");

    const sidebar =
        document.getElementById("sidebar");


    if (menuToggle && sidebar) {

        menuToggle.addEventListener(
            "click",
            function () {

                sidebar.classList.toggle("open");

            }
        );

    }


    /*
     * Close sidebar on mobile
     * after clicking a menu link.
     */

    const navLinks =
        document.querySelectorAll(
            ".nav-link"
        );


    navLinks.forEach(function (link) {

        link.addEventListener(
            "click",
            function () {

                if (
                    window.innerWidth <= 900
                ) {

                    sidebar.classList.remove(
                        "open"
                    );

                }

            }
        );

    });

});