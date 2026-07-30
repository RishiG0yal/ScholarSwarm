from utils.cache import _cache
from datetime import datetime, timezone, timedelta

DEMO_RESULT_ID = "demo1234"

DEMO_PAGE_TEXTS = {
    1: """Attention Is All You Need
Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin

Abstract
The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.0 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature.""",
    2: """Introduction
Recurrent neural networks, long short-term memory and gated recurrent neural networks in particular, have been firmly established as state of the art approaches in sequence modeling and transduction problems such as language modeling and machine translation. Numerous efforts have since continued to push the boundaries of recurrent language models and encoder-decoder architectures.

Recurrent models typically factor computation along the symbol positions of the input and output sequences. Aligning the positions to steps in computation time, they generate a sequence of hidden states ht, as a function of the previous hidden state ht−1 and the input for position t. This inherently sequential nature precludes parallelization within training examples, which becomes critical at longer sequence lengths, as memory constraints limit batching across examples.

The Transformer avoids this by relying entirely on an attention mechanism to draw global dependencies between input and output.""",
    3: """Background
The goal of reducing sequential computation also forms the foundation of the Extended Neural GPU, ByteNet and ConvS2S, all of which use convolutional neural networks as basic building block, computing hidden representations in parallel for all input and output positions. In these models, the number of operations required to relate signals from two arbitrary input or output positions grows in the distance between positions.

In the Transformer this is reduced to a constant number of operations, albeit at the cost of reduced effective resolution due to averaging attention-weighted positions, an effect we counteract with Multi-Head Attention.

Self-attention, sometimes called intra-attention, is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. Self-attention has been used successfully in a variety of tasks including reading comprehension, abstractive summarization, textual entailment and learning task-independent sentence representations.""",
    4: """Model Architecture
Most competitive neural sequence transduction models have an encoder-decoder structure. Here, the encoder maps an input sequence of symbol representations to a sequence of continuous representations. Given z, the decoder then generates an output sequence of symbols one element at a time.

The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder.

Encoder: The encoder is composed of a stack of N=6 identical layers. Each layer has two sub-layers. The first is a multi-head self-attention mechanism, and the second is a simple, position-wise fully connected feed-forward network.

Decoder: The decoder is also composed of a stack of N=6 identical layers. In addition to the two sub-layers in each encoder layer, the decoder inserts a third sub-layer, which performs multi-head attention over the output of the encoder stack.

Scaled Dot-Product Attention: We call our particular attention "Scaled Dot-Product Attention". The input consists of queries and keys of dimension dk, and values of dimension dv. We compute the dot products of the query with all keys, divide each by sqrt(dk), and apply a softmax function to obtain the weights on the values.

Attention(Q, K, V) = softmax(QK^T / sqrt(dk)) * V

Multi-Head Attention allows the model to jointly attend to information from different representation subspaces at different positions. MultiHead(Q,K,V) = Concat(head1,...,headh) * W^O""",
    5: """Positional Encoding
Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or absolute position of the tokens in the sequence. To this end, we add "positional encodings" to the input embeddings at the bottoms of the encoder and decoder stacks.

We use sine and cosine functions of different frequencies:
PE(pos,2i) = sin(pos/10000^(2i/dmodel))
PE(pos,2i+1) = cos(pos/10000^(2i/dmodel))""",
    6: """Why Self-Attention
In this section we compare various aspects of self-attention layers to the recurrent and convolutional layers commonly used for mapping one variable-length sequence of symbol representations to another sequence of equal length.

Total computational complexity per layer:
- Self-attention: O(n^2 * d)
- Recurrent: O(n * d^2)
- Convolutional: O(k * n * d^2)

Self-attention layers are faster than recurrent layers when the sequence length n is smaller than the representation dimensionality d, which is most often the case with sentence representations used by state-of-the-art models in machine translations.""",
    7: """Training
We trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. We trained our models on one machine with 8 NVIDIA P100 GPUs. For our base models using the hyperparameters described throughout the paper, each training step took about 0.4 seconds. We trained the base models for a total of 100,000 steps or 12 hours. For our big models, step time was 1.0 seconds. The big models were trained for 300,000 steps (3.5 days).

We used the Adam optimizer with beta1=0.9, beta2=0.98 and epsilon=10^-9.

Regularization: We employ three types of regularization during training: Residual Dropout with Pdrop=0.1, Label Smoothing with epsilon_ls=0.1.""",
    8: """Results
On the WMT 2014 English-to-German translation task, the big transformer model outperforms the best previously reported models including ensembles by more than 2.0 BLEU, establishing a new state-of-the-art BLEU score of 28.4.

On the WMT 2014 English-to-French translation task, our big model achieves a BLEU score of 41.0, outperforming all of the previously published single models, at less than 1/4 the training cost of the previous state-of-the-art model.

The Transformer (big) model achieves 28.4 BLEU on EN-DE and 41.0 BLEU on EN-FR. Training cost: 2.3×10^19 FLOPs.""",
}

DEMO_DATA = {
    "title": "Attention Is All You Need",
    "authors": "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin",
    "total_pages": 15,
    "file_type": "pdf",
    "summary": "This paper introduces the Transformer, a novel neural network architecture based entirely on attention mechanisms, dispensing with recurrence and convolutions entirely. The Transformer achieves state-of-the-art results on machine translation tasks, reaching 28.4 BLEU on WMT 2014 English-to-German and 41.0 BLEU on English-to-French. The model trains significantly faster than architectures based on recurrent or convolutional layers and generalizes well to other tasks.",
    "eli5_summary": "Imagine you're reading a book and instead of reading every word in order, you can instantly look at all the important words at the same time and figure out which ones are connected. That's what this paper invented — a new way for AI to read and understand language by letting it look at all the words at once and decide which ones matter most. It became the foundation for ChatGPT and most modern AI.",
    "reading_level": "Graduate",
    "readability_score": 28.4,
    "verified_count": 3,
    "flagged_count": 1,
    "claims": [
        {"text": "The Transformer achieves 28.4 BLEU on WMT 2014 English-to-German translation, improving over the best previously reported models by over 2 BLEU.", "page": 8, "verified": True, "confidence": 0.97, "critique": "Directly supported by Table 2 in the paper.", "source_quote": "our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU."},
        {"text": "The Transformer big model was trained for 3.5 days on 8 NVIDIA P100 GPUs.", "page": 7, "verified": True, "confidence": 0.94, "critique": "Supported by the training section.", "source_quote": "The big models were trained for 300,000 steps (3.5 days)."},
        {"text": "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions.", "page": 4, "verified": True, "confidence": 0.96, "critique": "Directly stated in the Multi-Head Attention section.", "source_quote": "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions."},
        {"text": "The Transformer requires minimal computational resources compared to all prior models.", "page": 2, "verified": False, "confidence": 0.28, "critique": "The paper states training costs are lower than some models but does not claim minimal resources compared to ALL prior models.", "source_quote": "requiring significantly less time to train"},
    ],
    "limitations": [
        "The model may struggle with tasks requiring strict sequential reasoning due to the lack of recurrence.",
        "Computational complexity is quadratic in sequence length O(n^2*d), making it expensive for very long sequences.",
        "Positional encodings are fixed sinusoidal functions; learned positional encodings were not extensively compared.",
        "Evaluation is primarily on machine translation; generalization to other modalities is not fully explored.",
    ],
    "flashcards": [
        {"front": "What is the main architectural innovation of this paper?", "back": "The Transformer architecture, which relies entirely on self-attention mechanisms and eliminates recurrence and convolution."},
        {"front": "What BLEU score did the Transformer achieve on WMT 2014 English-German?", "back": "28.4 BLEU, surpassing all previous models including ensembles by more than 2 BLEU."},
        {"front": "What is scaled dot-product attention?", "back": "Attention(Q,K,V) = softmax(QK^T / sqrt(dk)) * V — queries and keys of dimension dk are dot-producted, scaled, softmaxed, then applied to values."},
        {"front": "How many encoder/decoder layers does the base Transformer use?", "back": "N=6 identical layers in both the encoder and decoder stacks."},
        {"front": "What optimizer and hyperparameters were used for training?", "back": "Adam optimizer with beta1=0.9, beta2=0.98, epsilon=10^-9, with a custom learning rate schedule."},
        {"front": "Why were positional encodings added?", "back": "The model has no recurrence or convolution, so positional encodings inject information about token order using sine and cosine functions of different frequencies."},
    ],
    "key_terms": [
        {"term": "Self-Attention", "definition": "A mechanism where each position in the sequence attends to all positions to compute a representation."},
        {"term": "Multi-Head Attention", "definition": "Running attention h times in parallel, each with different learned projections, then concatenating outputs."},
        {"term": "Scaled Dot-Product Attention", "definition": "Attention computed as softmax(QK^T/sqrt(d_k))*V, where scaling by sqrt(d_k) prevents vanishing gradients."},
        {"term": "Encoder-Decoder", "definition": "Architecture where encoder processes input sequence and decoder generates output, connected by cross-attention."},
        {"term": "BLEU Score", "definition": "Bilingual Evaluation Understudy — standard metric for evaluating machine translation quality."},
        {"term": "Positional Encoding", "definition": "Sinusoidal embeddings added to token embeddings to inject position information since the model has no recurrence."},
        {"term": "Feed-Forward Network", "definition": "Two linear transformations with ReLU activation applied identically to each position: FFN(x) = max(0, xW1+b1)W2+b2."},
        {"term": "Layer Normalization", "definition": "Normalization applied after each sub-layer residual connection to stabilize training."},
    ],
    "tables": [
        {
            "page": 8,
            "table_index": 1,
            "headers": ["Model", "EN-DE BLEU", "EN-FR BLEU", "Training Cost (FLOPs)"],
            "rows": [
                ["ByteNet", "23.75", "—", "—"],
                ["GNMT + RL", "24.6", "39.92", "2.3×10¹⁹"],
                ["ConvS2S", "25.16", "40.46", "9.6×10¹⁸"],
                ["Transformer (base)", "27.3", "38.1", "3.3×10¹⁸"],
                ["Transformer (big)", "28.4", "41.0", "2.3×10¹⁹"],
            ],
            "raw_markdown": "| Model | EN-DE | EN-FR | Cost |\n|---|---|---|---|\n| Transformer (big) | 28.4 | 41.0 | 2.3×10¹⁹ |",
        }
    ],
    "figures": [],
    "equations": [
        {"page": 4, "latex": "Attention(Q, K, V) = softmax(QK^T / sqrt(dk)) * V", "description": "Scaled dot-product attention formula", "source": "regex"},
        {"page": 4, "latex": "MultiHead(Q,K,V) = Concat(head1,...,headh) * W^O", "description": "Multi-head attention formula", "source": "regex"},
    ],
    "citations": ["(Bahdanau et al., 2014)", "(Gehring et al., 2017)", "(Luong et al., 2015)", "(Sutskever et al., 2014)", "(Wu et al., 2016)"],
    "citations_count": 5,
    "result_id": DEMO_RESULT_ID,
    "_page_texts": DEMO_PAGE_TEXTS,
}


def preload_demo():
    _cache[DEMO_RESULT_ID] = {
        "data": DEMO_DATA,
        "created_at": datetime.now(timezone.utc) + timedelta(days=365),
    }
