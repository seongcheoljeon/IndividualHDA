"""Line alignment and tag sets behind the conflict review."""

from libs.text_diff import line_ops, render_html, tag_diff


def test_line_ops_align_equal_insert_delete_and_replace() -> None:
    ops = line_ops("a\nb\nc\nd", "a\nB\nc\ne\nf")
    assert ops == [
        ("equal", "a", "a"),
        ("replace", "b", "B"),
        ("equal", "c", "c"),
        ("replace", "d", "e"),
        ("replace", "", "f"),
    ]
    assert line_ops("", "") == [] and line_ops("x", "x") == [("equal", "x", "x")]
    assert line_ops("x\ny", "x") == [("equal", "x", "x"), ("delete", "y", "")]


def test_render_html_escapes_and_marks_the_changed_side_only() -> None:
    ops = line_ops("<b>same</b>\nold", "<b>same</b>\nnew")
    left = render_html(ops, "left", changed="red")
    right = render_html(ops, "right", changed="green")
    assert "&lt;b&gt;same&lt;/b&gt;" in left and "<b>" not in left
    assert left.count("background: red") == 1 and "old" in left
    assert right.count("background: green") == 1 and "new" in right
    assert (
        render_html([("insert", "", "x")], "left", changed="c") == "<div>&nbsp;</div>"
    )


def test_tag_diff_is_case_insensitive_and_ordered() -> None:
    assert tag_diff(["Water", "fire", "new"], ["water", "Smoke", "fire"]) == (
        ["new"],
        ["Smoke"],
        ["Water", "fire"],
    )
    assert tag_diff([], []) == ([], [], [])
