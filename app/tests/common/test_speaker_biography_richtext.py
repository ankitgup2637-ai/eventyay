from django import forms
from django.template import Context, Template

from eventyay.base.models import SpeakerProfile
from eventyay.common.forms.fields import RichTextField
from eventyay.common.forms.widgets import RichTextWidget
from eventyay.common.text.phrases import phrases
from eventyay.person.forms.profile import SpeakerProfileForm


def test_richtext_widget_format_value_empty():
    widget = RichTextWidget()
    assert widget.format_value(None) == ''
    assert widget.format_value('') == ''


def test_richtext_widget_format_value_legacy_markdown():
    widget = RichTextWidget()
    # Bold markdown
    formatted = widget.format_value('**Alice**')
    assert '<p><strong>Alice</strong></p>' in formatted

    # List markdown
    formatted_list = widget.format_value('* First item\n* Second item')
    assert '<ul>' in formatted_list
    assert '<li>First item</li>' in formatted_list
    assert '<li>Second item</li>' in formatted_list

    # Plain text
    formatted_plain = widget.format_value('Just plain text')
    assert '<p>Just plain text</p>' in formatted_plain


def test_richtext_widget_format_value_preserves_existing_html():
    widget = RichTextWidget()
    html = '<p>Already <strong>HTML</strong> content</p>'
    assert widget.format_value(html) == html


def test_richtext_widget_format_value_sanitizes_xss():
    widget = RichTextWidget()
    # Strips script tags
    dangerous = '<script>alert("xss")</script><p>Safe text</p>'
    formatted = widget.format_value(dangerous)
    assert '<script>' not in formatted
    assert '<p>Safe text</p>' in formatted

    # Strips dangerous attributes like onclick and javascript: links
    dangerous_attr = '<p onclick="evil()"><a href="javascript:alert(1)">link</a></p>'
    formatted_attr = widget.format_value(dangerous_attr)
    assert 'onclick' not in formatted_attr
    assert 'javascript:' not in formatted_attr


def test_speaker_profile_form_field_classes_and_widgets():
    form_meta = SpeakerProfileForm.Meta
    assert form_meta.widgets.get('biography') is RichTextWidget
    assert form_meta.field_classes.get('biography') is RichTextField

    # avatar_source and avatar_license must be plain text widgets, NOT RichTextWidget/Tiptap
    avatar_source_widget = form_meta.widgets.get('avatar_source')
    avatar_license_widget = form_meta.widgets.get('avatar_license')
    assert issubclass(type(avatar_source_widget), forms.Textarea)
    assert not issubclass(type(avatar_source_widget), RichTextWidget)
    assert issubclass(type(avatar_license_widget), forms.Textarea)
    assert not issubclass(type(avatar_license_widget), RichTextWidget)


def test_speaker_profile_biography_help_text():
    field = SpeakerProfile._meta.get_field('biography')
    assert field.help_text == phrases.base.use_richtext
    assert 'rich-text-hint' in str(phrases.base.use_richtext)


def test_rich_text_template_filter_renders_html_and_markdown():
    template = Template('{% load rich_text %}{{ content|rich_text }}')

    # HTML rendering
    rendered_html = template.render(Context({'content': '<p>Hello <strong>World</strong></p>'}))
    assert '<p>Hello <strong>World</strong></p>' in rendered_html

    # Legacy markdown rendering
    rendered_md = template.render(Context({'content': '**Bold Speaker**'}))
    assert '<strong>Bold Speaker</strong>' in rendered_md
