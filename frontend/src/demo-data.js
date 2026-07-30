const DEMO_DATA = {
  result_id: "demo1234",
  title: "Attention Is All You Need",
  authors: "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin",
  total_pages: 15,
  file_type: "pdf",
  summary:
    "This paper introduces the Transformer, a novel neural network architecture based entirely on attention mechanisms, dispensing with recurrence and convolutions entirely. The Transformer achieves state-of-the-art results on machine translation tasks, reaching 28.4 BLEU on WMT 2014 English-to-German and 41.0 BLEU on English-to-French. The model trains significantly faster than architectures based on recurrent or convolutional layers and generalizes well to other tasks.",
  eli5_summary:
    "Imagine you're reading a book and instead of reading every word in order, you can instantly look at all the important words at the same time and figure out which ones are connected. That's what this paper invented — a new way for AI to read and understand language by letting it look at all the words at once and decide which ones matter most. It turned out to be much faster and better than the old way of reading word-by-word, and it became the foundation for ChatGPT and most modern AI.",
  reading_level: "Graduate",
  readability_score: 28.4,
  verified_count: 3,
  flagged_count: 1,
  claims: [
    {
      text: "The Transformer achieves 28.4 BLEU on WMT 2014 English-to-German translation, improving over the best previously reported models by over 2 BLEU.",
      page: 8,
      verified: true,
      confidence: 0.97,
      critique: "Directly supported by Table 2 in the paper.",
      source_quote: "our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU.",
    },
    {
      text: "The Transformer model can be trained in 3.5 days on 8 NVIDIA P100 GPUs.",
      page: 7,
      verified: true,
      confidence: 0.92,
      critique: "Supported by the training cost section of the paper.",
      source_quote: "The big models were trained for 300,000 steps, taking about 3.5 days on 8 P100 GPUs.",
    },
    {
      text: "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions.",
      page: 4,
      verified: true,
      confidence: 0.95,
      critique: "Directly stated in the Multi-Head Attention section.",
      source_quote: "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions.",
    },
    {
      text: "The Transformer requires minimal computational resources compared to all prior models.",
      page: 2,
      verified: false,
      confidence: 0.31,
      critique: "The paper states training costs are lower than recurrent models but does not claim minimal resources compared to all prior models. This is an overstatement.",
      source_quote: "Training costs are a fraction of those of the models described above.",
    },
  ],
  limitations: [
    "The model may struggle with tasks requiring strict sequential or positional reasoning due to the lack of recurrence.",
    "Computational complexity is quadratic in sequence length, making it expensive for very long sequences.",
    "The paper evaluates primarily on machine translation; generalization to other modalities is not fully explored.",
    "Positional encodings are fixed sinusoidal functions; learned positional encodings were not extensively compared.",
  ],
  flashcards: [
    {
      front: "What is the main architectural innovation in this paper?",
      back: "The Transformer architecture, which relies entirely on self-attention mechanisms and eliminates recurrence and convolution.",
    },
    {
      front: "What is multi-head attention?",
      back: "Running attention multiple times in parallel on linearly projected queries, keys, and values, then concatenating and projecting the outputs.",
    },
    {
      front: "What BLEU score did the Transformer achieve on WMT 2014 English-German?",
      back: "28.4 BLEU, surpassing all previous models including ensembles by more than 2 BLEU.",
    },
    {
      front: "Why did the authors eliminate recurrence?",
      back: "To allow for more parallelization during training, reduce sequential computation, and enable modeling of long-range dependencies without distance constraints.",
    },
    {
      front: "What is the purpose of positional encodings?",
      back: "Since the model has no recurrence or convolution, positional encodings inject information about the position of each token in the sequence.",
    },
  ],
  key_terms: [
    { term: "Self-Attention", definition: "A mechanism where each position in the sequence attends to all positions to compute a representation." },
    { term: "Multi-Head Attention", definition: "Running attention h times in parallel, each with different learned projections." },
    { term: "Encoder-Decoder", definition: "Architecture where encoder processes input and decoder generates output, connected by attention." },
    { term: "BLEU Score", definition: "Bilingual Evaluation Understudy — a metric for evaluating machine translation quality." },
    { term: "Positional Encoding", definition: "Sinusoidal embeddings added to token embeddings to provide position information." },
    { term: "Scaled Dot-Product", definition: "Attention computed as softmax(QK^T / sqrt(d_k)) * V." },
    { term: "Feed-Forward Network", definition: "Two linear transformations with ReLU activation applied identically to each position." },
    { term: "Layer Normalization", definition: "Normalization applied after each sub-layer to stabilize training." },
  ],
  tables: [
    {
      page: 8,
      table_index: 1,
      headers: ["Model", "EN-DE BLEU", "EN-FR BLEU", "Training Cost (FLOPs)"],
      rows: [
        ["ByteNet", "23.75", "-", ""],
        ["Deep-Att + PosUnk", "-", "39.2", "1.0 × 10²⁰"],
        ["GNMT + RL", "24.6", "39.92", "2.3 × 10¹⁹"],
        ["ConvS2S", "25.16", "40.46", "9.6 × 10¹⁸"],
        ["MoE", "26.03", "40.56", "2.0 × 10¹⁹"],
        ["Transformer (base)", "27.3", "38.1", "3.3 × 10¹⁸"],
        ["Transformer (big)", "28.4", "41.0", "2.3 × 10¹⁹"],
      ],
      raw_markdown: "| Model | EN-DE BLEU | EN-FR BLEU | Training Cost |\n|---|---|---|---|\n| Transformer (big) | 28.4 | 41.0 | 2.3 × 10¹⁹ |",
    },
  ],
  figures: [],
  equations: [
    { page: 3, latex: "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V", source: "regex", fallback_text: "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V" },
    { page: 3, latex: "MultiHead(Q, K, V) = Concat(head_1, ..., head_h) * W^O", source: "regex", fallback_text: "MultiHead(Q, K, V)" },
  ],
  citations: ["(Bahdanau et al., 2014)", "(Gehring et al., 2017)", "(Luong et al., 2015)", "(Sutskever et al., 2014)", "(Wu et al., 2016)", "[1]", "[2]", "[3]"],
  citations_count: 8,
};

export default DEMO_DATA;
