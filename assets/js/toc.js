(function () {
    var toc = document.getElementById("post-toc");
    if (!toc) {
        return;
    }

    var headings = Array.prototype.slice.call(document.querySelectorAll(".article h2, .article h3"));
    var tocWrapper = toc.closest(".article-toc");

    if (headings.length < 2) {
        if (tocWrapper) {
            tocWrapper.hidden = true;
        }
        return;
    }

    var usedIds = {};

    headings.forEach(function (heading) {
        var currentId = heading.getAttribute("id");

        if (!currentId) {
            var slug = heading.textContent.trim()
                .toLowerCase()
                .replace(/[^\w\u4e00-\u9fa5]+/g, "-")
                .replace(/^-+|-+$/g, "") || "section";
            var baseSlug = slug;
            var counter = 2;

            while (document.getElementById(slug) || usedIds[slug]) {
                slug = baseSlug + "-" + counter;
                counter += 1;
            }

            heading.setAttribute("id", slug);
            currentId = slug;
        }

        usedIds[currentId] = true;
    });

    var list = document.createElement("ol");

    headings.forEach(function (heading) {
        var item = document.createElement("li");
        var link = document.createElement("a");

        item.className = "toc-level-" + heading.tagName.substring(1);
        link.href = "#" + heading.getAttribute("id");
        link.textContent = heading.textContent;

        item.appendChild(link);
        list.appendChild(item);
    });

    toc.appendChild(list);
    tocWrapper.hidden = false;
    document.querySelector(".article-shell").classList.add("has-toc");
})();
