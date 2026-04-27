from app.models import MerchItem

INVENTORY: list[MerchItem] = [
    # NumPy
    MerchItem(project_name="NumPy", type="T-Shirt", quantity=50, price=29.99, logo_url="https://numpy.org/images/logo.svg"),
    MerchItem(project_name="NumPy", type="Socks", quantity=100, price=12.99, logo_url="https://numpy.org/images/logo.svg"),
    MerchItem(project_name="NumPy", type="Sticker", quantity=200, price=4.99, logo_url="https://numpy.org/images/logo.svg"),
    # Pandas
    MerchItem(project_name="Pandas", type="T-Shirt", quantity=30, price=29.99, logo_url="https://pandas.pydata.org/static/img/pandas_mark.svg"),
    MerchItem(project_name="Pandas", type="Socks", quantity=75, price=12.99, logo_url="https://pandas.pydata.org/static/img/pandas_mark.svg"),
    MerchItem(project_name="Pandas", type="Sticker", quantity=150, price=4.99, logo_url="https://pandas.pydata.org/static/img/pandas_mark.svg"),
    # Matplotlib
    MerchItem(project_name="Matplotlib", type="T-Shirt", quantity=40, price=29.99, logo_url="https://matplotlib.org/_static/logo_dark.svg"),
    MerchItem(project_name="Matplotlib", type="Socks", quantity=80, price=12.99, logo_url="https://matplotlib.org/_static/logo_dark.svg"),
    MerchItem(project_name="Matplotlib", type="Sticker", quantity=175, price=4.99, logo_url="https://matplotlib.org/_static/logo_dark.svg"),
    # Scikit-Learn
    MerchItem(project_name="Scikit-Learn", type="T-Shirt", quantity=35, price=29.99, logo_url="https://scikit-learn.org/stable/_static/scikit-learn-logo-small.png"),
    MerchItem(project_name="Scikit-Learn", type="Socks", quantity=90, price=12.99, logo_url="https://scikit-learn.org/stable/_static/scikit-learn-logo-small.png"),
    MerchItem(project_name="Scikit-Learn", type="Sticker", quantity=160, price=4.99, logo_url="https://scikit-learn.org/stable/_static/scikit-learn-logo-small.png"),
    # TensorFlow
    MerchItem(project_name="TensorFlow", type="T-Shirt", quantity=25, price=29.99, logo_url="https://www.tensorflow.org/images/tf_logo_social.png"),
    MerchItem(project_name="TensorFlow", type="Socks", quantity=60, price=12.99, logo_url="https://www.tensorflow.org/images/tf_logo_social.png"),
    MerchItem(project_name="TensorFlow", type="Sticker", quantity=140, price=4.99, logo_url="https://www.tensorflow.org/images/tf_logo_social.png"),
    # PyTorch
    MerchItem(project_name="PyTorch", type="T-Shirt", quantity=20, price=29.99, logo_url="https://pytorch.org/assets/images/pytorch-logo.png"),
    MerchItem(project_name="PyTorch", type="Socks", quantity=55, price=12.99, logo_url="https://pytorch.org/assets/images/pytorch-logo.png"),
    MerchItem(project_name="PyTorch", type="Sticker", quantity=120, price=4.99, logo_url="https://pytorch.org/assets/images/pytorch-logo.png"),
    # Keras
    MerchItem(project_name="Keras", type="T-Shirt", quantity=15, price=29.99, logo_url="https://keras.io/img/logo.png"),
    MerchItem(project_name="Keras", type="Socks", quantity=40, price=12.99, logo_url="https://keras.io/img/logo.png"),
    MerchItem(project_name="Keras", type="Sticker", quantity=100, price=4.99, logo_url="https://keras.io/img/logo.png"),
    # LangChain
    MerchItem(project_name="LangChain", type="T-Shirt", quantity=10, price=29.99, logo_url="https://avatars.githubusercontent.com/u/126733545"),
    MerchItem(project_name="LangChain", type="Socks", quantity=30, price=12.99, logo_url="https://avatars.githubusercontent.com/u/126733545"),
    MerchItem(project_name="LangChain", type="Sticker", quantity=80, price=4.99, logo_url="https://avatars.githubusercontent.com/u/126733545"),
    # spaCy
    MerchItem(project_name="spaCy", type="T-Shirt", quantity=18, price=29.99, logo_url="https://spacy.io/_next/static/media/logo.7e43e5d8.svg"),
    MerchItem(project_name="spaCy", type="Sticker", quantity=90, price=4.99, logo_url="https://spacy.io/_next/static/media/logo.7e43e5d8.svg"),
    # Polars
    MerchItem(project_name="Polars", type="T-Shirt", quantity=12, price=29.99, logo_url="https://raw.githubusercontent.com/pola-rs/polars-static/master/logos/polars-logo-dark.svg"),
    MerchItem(project_name="Polars", type="Sticker", quantity=70, price=4.99, logo_url="https://raw.githubusercontent.com/pola-rs/polars-static/master/logos/polars-logo-dark.svg"),
    # Hugging Face
    MerchItem(project_name="Hugging Face", type="T-Shirt", quantity=8, price=29.99, logo_url="https://huggingface.co/front/assets/huggingface_logo-noborder.svg"),
    MerchItem(project_name="Hugging Face", type="Sticker", quantity=60, price=4.99, logo_url="https://huggingface.co/front/assets/huggingface_logo-noborder.svg"),
]
