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

    var usedIds = Object.create(null);

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
    var groups = [];
    var entries = [];
    var currentGroup = null;
    var activeEntry = null;
    var fragmentEntry = null;
    var fragmentScrollTop = null;
    var readingOffset = 0;
    var framePending = false;
    var measureOffset = true;

    function setExpanded(group, expanded) {
        if (group.button.getAttribute("aria-expanded") === String(expanded)) {
            return;
        }
        group.children.hidden = !expanded;
        group.button.setAttribute("aria-expanded", String(expanded));
        group.button.setAttribute("aria-label", (expanded ? "收起" : "展开") + "「" + group.label + "」子章节");
    }

    function syncGroups() {
        groups.forEach(function (group) {
            var isCurrent = activeEntry && activeEntry.group === group;
            group.item.classList.toggle("is-current-chapter", Boolean(isCurrent));
            if (!group.children) {
                return;
            }

            var expanded = group.manualExpanded === null ? Boolean(isCurrent) : group.manualExpanded;
            if (fragmentEntry && fragmentEntry.group === group) {
                expanded = true;
            }
            // Keep keyboard focus visible when reading moves to a different chapter.
            if (!expanded && group.children.contains(document.activeElement)) {
                expanded = true;
            }
            setExpanded(group, expanded);
        });
    }

    function selectEntry(entry) {
        if (activeEntry !== entry) {
            if (activeEntry) {
                activeEntry.link.removeAttribute("aria-current");
            }
            activeEntry = entry;
            activeEntry.link.setAttribute("aria-current", "location");
        }
        syncGroups();
    }

    headings.forEach(function (heading, index) {
        var item = document.createElement("li");
        var link = document.createElement("a");

        item.className = "toc-level-" + heading.tagName.substring(1);
        link.href = "#" + encodeURIComponent(heading.getAttribute("id"));
        link.textContent = heading.textContent.trim();

        if (heading.tagName === "H2") {
            var row = document.createElement("div");
            row.className = "toc-chapter-row";
            row.appendChild(link);
            item.appendChild(row);
            list.appendChild(item);
            currentGroup = {
                item: item,
                row: row,
                label: link.textContent,
                children: null,
                button: null,
                manualExpanded: null
            };
            groups.push(currentGroup);
        } else if (currentGroup) {
            if (!currentGroup.children) {
                var group = currentGroup;
                var children = document.createElement("ol");
                var groupId = "toc-subsections-" + index;
                while (document.getElementById(groupId) || usedIds[groupId]) {
                    groupId += "-toc";
                }
                usedIds[groupId] = true;
                children.id = groupId;
                children.className = "toc-subsections";

                var button = document.createElement("button");
                button.type = "button";
                button.className = "toc-toggle";
                button.setAttribute("aria-controls", groupId);
                group.children = children;
                group.button = button;
                button.addEventListener("click", function () {
                    group.manualExpanded = group.children.hidden;
                    if (fragmentEntry && fragmentEntry.group === group) {
                        fragmentEntry = null;
                        fragmentScrollTop = null;
                    }
                    syncGroups();
                });

                group.row.appendChild(button);
                group.item.appendChild(children);
                setExpanded(group, false);
            }
            item.appendChild(link);
            currentGroup.children.appendChild(item);
        } else {
            // A leading H3 remains navigable even if an article skips its parent H2.
            item.appendChild(link);
            list.appendChild(item);
        }

        entries.push({ heading: heading, link: link, group: currentGroup });
        link.addEventListener("click", function (event) {
            if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) {
                return;
            }
            // Repeating the current fragment does not emit a hashchange event.
            if (window.location.hash === link.hash) {
                revealHashTarget();
            }
        });
    });

    toc.appendChild(list);
    if (tocWrapper) {
        tocWrapper.hidden = false;
    }
    var shell = document.querySelector(".article-shell");
    if (shell) {
        shell.classList.add("has-toc");
    }

    function updateReadingPosition() {
        framePending = false;
        if (measureOffset) {
            readingOffset = parseFloat(window.getComputedStyle(headings[0]).scrollMarginTop) || 0;
            measureOffset = false;
        }

        var current = entries[0];
        entries.forEach(function (entry) {
            if (entry.heading.getBoundingClientRect().top <= readingOffset + 1) {
                current = entry;
            }
        });
        if (fragmentEntry) {
            if (fragmentScrollTop === null) {
                fragmentScrollTop = window.scrollY;
            } else if (Math.abs(window.scrollY - fragmentScrollTop) > 1) {
                fragmentEntry = null;
                fragmentScrollTop = null;
            }
            if (fragmentEntry) {
                current = fragmentEntry;
            }
        }
        // Heading positions remain stable when the mobile TOC below the article grows.
        selectEntry(current);
    }

    function scheduleUpdate() {
        if (!framePending) {
            framePending = true;
            window.requestAnimationFrame(updateReadingPosition);
        }
    }

    function revealHashTarget() {
        fragmentEntry = null;
        fragmentScrollTop = null;
        var id;
        try {
            id = decodeURIComponent(window.location.hash.substring(1));
        } catch (error) {
            return;
        }
        var entry = entries.filter(function (candidate) {
            return candidate.heading.id === id;
        })[0];
        if (entry) {
            // Reveal this target only until reading continues; button choices persist.
            fragmentEntry = entry;
            selectEntry(entry);
        }
        measureOffset = true;
        scheduleUpdate();
    }

    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", function () {
        measureOffset = true;
        scheduleUpdate();
    });
    window.addEventListener("load", function () {
        measureOffset = true;
        scheduleUpdate();
    });
    window.addEventListener("hashchange", revealHashTarget);
    toc.addEventListener("focusout", scheduleUpdate);
    revealHashTarget();
    scheduleUpdate();
})();
