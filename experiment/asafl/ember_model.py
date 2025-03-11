import torch
import torch.nn as nn
import torch.nn.functional as F
# from torchinfo import summary


class EmberModel(nn.Module):
    def __init__(self, input_features=2381, output_features=1, input_dim=261, embedding_size=8):
        super(EmberModel, self).__init__()

        self.input_features = input_features
        self.input_dim = input_dim
        self.embedding_size = embedding_size

        self.embedding = nn.Embedding(input_dim, embedding_size)
        self.conv_feat = nn.Conv1d(in_channels=embedding_size, out_channels=128, kernel_size=15, stride=15, padding=0)
        self.conv_attn = nn.Conv1d(in_channels=embedding_size, out_channels=128, kernel_size=15, stride=15, padding=0)

        self.global_max_pool = nn.AdaptiveMaxPool1d(1)
        self.fc1 = nn.Linear(128, 128)
        self.fc2 = nn.Linear(128, output_features)

    def forward(self, x):
        assert x.shape[1] == self.input_features, f"Expected input shape (batch_size, {self.input_features}), got {x.shape}"
        x = self.embedding(x.long())  
        x = x.permute(0, 2, 1)  

        feat = F.relu(self.conv_feat(x))  
        attn = torch.sigmoid(self.conv_attn(x))  

        gated = feat * attn
        feat_vector = self.global_max_pool(gated).squeeze(-1)

        dense = F.relu(self.fc1(feat_vector))
        out = torch.sigmoid(self.fc2(dense))

        return out

# if __name__ == "__main__":
#     model = EmberModel()
#     print(model)
#     summary(model, input_size=(1, 2381))

#     # Generate Fake Data
#     batch_size = 16
#     input_features = 2381
#     fake_input = torch.randint(0, 261, (batch_size, input_features))

#     model.eval()
#     with torch.no_grad():
#         output = model(fake_input)

#     print("Output shape:", output.shape)
#     print("Sample Output:", output)

#     model.train()
#     optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
#     criterion = nn.BCELoss()

#     fake_labels = torch.randint(0, 2, (batch_size, 1), dtype=torch.float32)

#     optimizer.zero_grad()
#     predictions = model(fake_input)
#     loss = criterion(predictions, fake_labels)
#     loss.backward()
#     optimizer.step()

#     print("Training Loss:", loss.item())
