from django import forms


class ChatForm(forms.Form):
    question = forms.CharField(
        label="Tu consulta",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Escribe tu pregunta legal o consulta de tu causa...",
            "class": "form-control",
            "maxlength": 3000,
        }),
        max_length=3000,
        required=True,
    )