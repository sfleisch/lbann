import unittest
import onnx

from lbann.onnx.l2o import parseLbannLayer
from lbann.onnx.util import list2LbannList, getNodeAttributeByName
import lbann.proto as lp
from lbann.proto import lbann_pb2

class TestLbann2OnnxLayer(unittest.TestCase):
    def _assertFields(self, l, o):
        if len(l) > 1:
            self.skipTest("One LBANN layer is converted to more than one ONNX operators, so they cannot be compared.")

        l = l[0]

        attributeNames = set([x.name for x in l.attribute]) | set([x.name for x in o.attribute])
        attributeNames -= set(["lbannOp", "lbannDataLayout"])
        for attributeName in attributeNames:

            defVal = "DEFAULT_VALUE"
            lbannAttribute = getNodeAttributeByName(l, attributeName, defVal)
            onnxAttribute = getNodeAttributeByName(o, attributeName, defVal)

            self.assertNotEqual(lbannAttribute, defVal, (l, attributeName, lbannAttribute))
            self.assertNotEqual(onnxAttribute, defVal, (o, attributeName, onnxAttribute))

            assertFunc = self.assertEqual
            if isinstance(lbannAttribute, float) and isinstance(onnxAttribute, float):
                assertFunc = self.assertAlmostEqual

            assertFunc(
                lbannAttribute,
                onnxAttribute,
                msg=attributeName
            )

    def _test_l2o_layer_convolution(self, numDims, hasBias):
        N, C_in, H = (256, 3, 224)
        C_out = 64
        K, P, S, D = (3, 1, 1, 1)
        G = 1

        onnxConv = onnx.helper.make_node(
            "Conv",
            inputs=["x","W"] + (["b"] if hasBias else []),
            outputs=["y"],
            kernel_shape=[K]*numDims,
            pads=[P]*(numDims*2),
            strides=[S]*numDims,
            dilations=[D]*numDims,
            group=G
        )

        layer = lp.Convolution(
            lp.Input(name="x"),
            num_dims=numDims,
            num_output_channels=C_out,
            has_vectors=False,
            conv_dims_i=K,
            conv_pads_i=P,
            conv_strides_i=S,
            conv_dilations_i=D,
            num_groups=G,
            has_bias=hasBias
        )
        lbannConv = parseLbannLayer(layer.export_proto(), {"x_0": (N, C_in, H, H)})["nodes"]

        self._assertFields(lbannConv, onnxConv)

    def test_l2o_layer_convolution_bias(self):
        self._test_l2o_layer_convolution(numDims=2, hasBias=True)

    def test_l2o_layer_convolution_no_bias(self):
        self._test_l2o_layer_convolution(numDims=2, hasBias=False)

    def test_l2o_layer_convolution_3D_bias(self):
        self._test_l2o_layer_convolution(numDims=3, hasBias=True)

    def test_l2o_layer_convolution_3D_no_bias(self):
        self._test_l2o_layer_convolution(numDims=3, hasBias=False)

    def _test_l2o_layer_pooling(self, numDims, poolMode, onnxOp):
        N, C, H = (256, 3, 224)
        K, P, S = (3, 1, 1)

        onnxPooling = onnx.helper.make_node(
            onnxOp,
            inputs=["x"],
            outputs=["y"],
            kernel_shape=[K]*numDims,
            pads=[P]*(numDims*2),
            strides=[S]*numDims,
        )

        layer = lp.Pooling(
            lp.Input(name="x"),
            num_dims=numDims,
            has_vectors=False,
            pool_dims_i=K,
            pool_pads_i=P,
            pool_strides_i=S,
            pool_mode=poolMode
        )
        lbannPooling = parseLbannLayer(layer.export_proto(), {"x_0": (N, C, H, H)})["nodes"]

        self._assertFields(lbannPooling, onnxPooling)

    def test_l2o_layer_pooling_max(self):
        self._test_l2o_layer_pooling(numDims=2, poolMode="max", onnxOp="MaxPool")

    def test_l2o_layer_pooling_average(self):
        self._test_l2o_layer_pooling(numDims=2, poolMode="average", onnxOp="AveragePool")

    def test_l2o_layer_pooling_max_3d(self):
        self._test_l2o_layer_pooling(numDims=3, poolMode="max", onnxOp="MaxPool")

    def test_l2o_layer_pooling_average_3d(self):
        self._test_l2o_layer_pooling(numDims=3, poolMode="average", onnxOp="AveragePool")

    def test_l2o_layer_batch_normalization(self):
        N, C, H, W = (100, 200, 300, 400)
        decay = 0.95
        epsilon = 1e-6

        onnxBN = onnx.helper.make_node(
            "BatchNormalization",
            inputs=["x", "scale", "B", "mean", "var"],
            outputs=["y"],
            epsilon=epsilon,
            momentum=decay,
            spatial=1
        )

        layer = lp.BatchNormalization(
            lp.Input(name="x"),
            decay=decay, epsilon=epsilon,
        )
        lbannBN = parseLbannLayer(layer.export_proto(), {"x_0": (N, C, H, W)})["nodes"]

        self._assertFields(lbannBN, onnxBN)

    def test_l2o_layer_relu(self):
        N, C, H, W = (100, 200, 300, 400)

        onnxRelu = onnx.helper.make_node(
            "Relu",
            inputs=["x"],
            outputs=["y"],
        )

        layer = lp.Relu(
            lp.Input(name="x"),
        )
        lbannRelu = parseLbannLayer(layer.export_proto(), {"x_0": (N, C, H, W)})["nodes"]

        self._assertFields(lbannRelu, onnxRelu)


if __name__ == "__main__":
    unittest.main()
